from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import SeedIssue, SeedPayment, Farmer, Booking, SeedRateMaster
from app.auth import current_user, audit
from datetime import date, datetime

router = APIRouter()

@router.get('/issues')
def list_seed_issues(farmer_id: int = None, booking_id: int = None, variety: str = '', status: str = '', date_from: str = '', date_to: str = '', db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(SeedIssue)
    if farmer_id: q = q.filter(SeedIssue.farmer_id == farmer_id)
    if booking_id: q = q.filter(SeedIssue.booking_id == booking_id)
    if variety: q = q.filter(SeedIssue.variety.ilike(f'%{variety}%'))
    if status: q = q.filter(SeedIssue.status == status)
    if date_from: q = q.filter(SeedIssue.issue_date >= date.fromisoformat(date_from))
    if date_to: q = q.filter(SeedIssue.issue_date <= date.fromisoformat(date_to))
    
    out = []
    for s in q.order_by(SeedIssue.id.desc()).all():
        paid = sum(p.amount for p in s.payments if p.status == 'Active')
        bal = s.total_value - paid
        p_status = 'Completed' if bal <= 0 and s.total_value > 0 else ('Partial' if paid > 0 else 'Not Paid')
        out.append({
            'id': s.id, 'farmer': db.get(Farmer, s.farmer_id).name if s.farmer_id else '',
            'farmer_id': s.farmer_id, 'farmer_name': db.get(Farmer, s.farmer_id).name if s.farmer_id else '',
            'booking_id': s.booking_id, 'variety': s.variety, 'issue_date': str(s.issue_date),
            'packets': s.packets, 'rate': s.rate_per_packet, 'total_value': s.total_value,
            'paid': paid, 'balance': bal, 'status': s.status, 'payment_status': p_status
        })
    return out

@router.post('/issues')
async def create_seed_issue(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    d = await request.json()
    packets = float(d.get('packets', 0))
    rate = float(d.get('rate_per_packet', 0))
    
    # Auto-lookup rate if not provided
    if not rate and d.get('variety_id') and d.get('season_id'):
        dt = date.fromisoformat(d.get('issue_date') or str(date.today()))
        r = db.query(SeedRateMaster).filter(
            SeedRateMaster.variety_id == d['variety_id'],
            SeedRateMaster.season_id == d['season_id'],
            SeedRateMaster.active == True,
            SeedRateMaster.effective_from <= dt,
            (SeedRateMaster.effective_to == None) | (SeedRateMaster.effective_to >= dt)
        ).order_by(SeedRateMaster.effective_from.desc()).first()
        if r: rate = r.rate_per_packet
    
    s = SeedIssue(
        booking_id=int(d['booking_id']),
        farmer_id=int(d['farmer_id']),
        booking_variety_id=d.get('booking_variety_id'),
        supplier_id=d.get('supplier_id'),
        variety=d['variety'],
        issue_date=date.fromisoformat(d.get('issue_date') or str(date.today())),
        packets=packets,
        packet_weight_kg=float(d.get('packet_weight_kg', 0)),
        rate_per_packet=rate,
        total_value=packets * rate,
        challan_ref=d.get('challan_ref'),
        vehicle_no=d.get('vehicle_no'),
        remarks=d.get('remarks'),
        created_by_id=user.id,
        status='Active'
    )
    db.add(s)
    db.flush()
    audit(db, user, 'SeedIssue', s.id, 'CREATE', f'{packets} packets')
    db.commit()
    return {'id': s.id, 'total_value': s.total_value}

@router.put('/issues/{id}/cancel')
async def cancel_seed_issue(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    d = await request.json()
    s = db.get(SeedIssue, id)
    if not s: raise HTTPException(404, 'Not found')
    s.status = 'Cancelled'
    s.cancelled_by_id = user.id
    s.cancelled_at = datetime.utcnow()
    s.cancellation_reason = d.get('reason')
    db.commit()
    return {'ok': True}

@router.get('/payments')
def list_seed_payments(farmer_id: int = None, booking_id: int = None, status: str = '', db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(SeedPayment)
    if farmer_id: q = q.filter(SeedPayment.farmer_id == farmer_id)
    if booking_id: q = q.filter(SeedPayment.booking_id == booking_id)
    if status: q = q.filter(SeedPayment.status == status)
    
    return [{'id': p.id, 'seed_issue_id': p.seed_issue_id, 'farmer_id': p.farmer_id, 'booking_id': p.booking_id, 'payment_date': str(p.payment_date), 'amount': p.amount, 'mode': p.mode, 'status': p.status} for p in q.order_by(SeedPayment.id.desc()).all()]

@router.post('/payments')
async def create_seed_payment(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    d = await request.json()
    s = db.get(SeedIssue, int(d['seed_issue_id']))
    if not s: raise HTTPException(400, 'Seed issue not found')
    
    p = SeedPayment(
        seed_issue_id=s.id,
        booking_id=s.booking_id,
        farmer_id=s.farmer_id,
        payment_date=date.fromisoformat(d.get('payment_date') or str(date.today())),
        amount=float(d['amount']),
        mode=d.get('mode'),
        reference_no=d.get('reference_no'),
        remarks=d.get('remarks'),
        created_by_id=user.id,
        status='Active'
    )
    db.add(p)
    db.flush()
    audit(db, user, 'SeedPayment', p.id, 'CREATE', str(p.amount))
    db.commit()
    return {'id': p.id}

@router.put('/payments/{id}/cancel')
async def cancel_seed_payment(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    d = await request.json()
    p = db.get(SeedPayment, id)
    if not p: raise HTTPException(404, 'Not found')
    p.status = 'Cancelled'
    p.cancelled_by_id = user.id
    p.cancelled_at = datetime.utcnow()
    p.cancellation_reason = d.get('reason')
    db.commit()
    return {'ok': True}

@router.get('/summary/{farmer_id}')
def farmer_seed_summary(farmer_id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    issues = db.query(SeedIssue).filter(SeedIssue.farmer_id == farmer_id, SeedIssue.status == 'Active').all()
    total_value = sum(i.total_value for i in issues)
    
    paid_query = db.query(func.sum(SeedPayment.amount)).filter(SeedPayment.status == 'Active')
    paid_by_farmer = paid_query.filter(SeedPayment.farmer_id == farmer_id).scalar() or 0
    paid_fallback = paid_query.join(SeedIssue).filter(SeedIssue.farmer_id == farmer_id).scalar() or 0
    paid = max(paid_by_farmer, paid_fallback)
    
    balance = total_value - paid
    status = 'Completed' if balance <= 0 and total_value > 0 else ('Excess' if paid > total_value > 0 else ('Partial' if paid > 0 else 'Not Paid'))
    
    return {'total_value': total_value, 'paid': paid, 'balance': balance, 'status': status}

@router.get('/booking-summary/{booking_id}')
def booking_seed_summary(booking_id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    issues = db.query(SeedIssue).filter(SeedIssue.booking_id == booking_id, SeedIssue.status == 'Active').all()
    total_value = sum(i.total_value for i in issues)
    
    paid_query = db.query(func.sum(SeedPayment.amount)).filter(SeedPayment.status == 'Active')
    paid_by_booking = paid_query.filter(SeedPayment.booking_id == booking_id).scalar() or 0
    paid_fallback = paid_query.join(SeedIssue).filter(SeedIssue.booking_id == booking_id).scalar() or 0
    paid = max(paid_by_booking, paid_fallback)
    
    balance = total_value - paid
    status = 'Completed' if balance <= 0 and total_value > 0 else ('Excess' if paid > total_value > 0 else ('Partial' if paid > 0 else 'Not Paid'))
    
    return {'total_value': total_value, 'paid': paid, 'balance': balance, 'status': status}
