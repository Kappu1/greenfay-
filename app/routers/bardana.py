from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import BardanaIssue, Farmer, Commitment
from app.auth import current_user, audit
from datetime import date, datetime

router = APIRouter()

@router.get('/bardana')
@router.get('/bardana/')
def list_bardana(farmer_id: int = None, booking_id: int = None, month: str = '', date_from: str = '', date_to: str = '', db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(BardanaIssue)
    if farmer_id: q = q.filter(BardanaIssue.farmer_id == farmer_id)
    if booking_id: q = q.filter(BardanaIssue.booking_id == booking_id)
    if month: q = q.filter(BardanaIssue.contract_month == month)
    if date_from: q = q.filter(BardanaIssue.issue_date >= date.fromisoformat(date_from))
    if date_to: q = q.filter(BardanaIssue.issue_date <= date.fromisoformat(date_to))
    
    return [{'id': x.id, 'farmer': db.get(Farmer, x.farmer_id).name if x.farmer_id else '', 'booking_id': x.booking_id, 'issue_date': str(x.issue_date), 'contract_month': x.contract_month, 'bags_issued': x.bags_issued, 'challan_ref': x.challan_ref, 'vehicle_no': x.vehicle_no, 'status': x.status} for x in q.order_by(BardanaIssue.id.desc()).all()]

@router.post('/bardana')
@router.post('/bardana/')
async def create_bardana(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    d = await request.json()
    x = BardanaIssue(
        farmer_id=int(d['farmer_id']),
        booking_id=int(d['booking_id']),
        booking_variety_id=d.get('booking_variety_id'),
        contract_month=d.get('contract_month'),
        issue_date=date.fromisoformat(d.get('issue_date') or str(date.today())),
        bardana_type=d.get('bardana_type', 'Potato Storage Bag'),
        bardana_type_id=d.get('bardana_type_id'),
        bags_issued=float(d['bags_issued']),
        challan_ref=d.get('challan_ref'),
        vehicle_no=d.get('vehicle_no'),
        remarks=d.get('remarks'),
        created_by_id=user.id,
        status='Active'
    )
    db.add(x)
    db.flush()
    audit(db, user, 'BardanaIssue', x.id, 'CREATE', str(x.bags_issued))
    db.commit()
    return {'id': x.id}

@router.put('/bardana/{id}/cancel')
async def cancel_bardana(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    d = await request.json()
    x = db.get(BardanaIssue, id)
    if not x: raise HTTPException(404, 'Not found')
    x.status = 'Cancelled'
    x.cancelled_by_id = user.id
    x.cancelled_at = datetime.utcnow()
    x.cancellation_reason = d.get('reason')
    db.commit()
    return {'ok': True}

@router.get('/bardana/summary/{booking_id}')
def bardana_summary(booking_id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    required = db.query(func.sum(Commitment.contracted_bags)).filter(Commitment.booking_id == booking_id, Commitment.status != 'Cancelled').scalar() or 0
    issued = db.query(func.sum(BardanaIssue.bags_issued)).filter(BardanaIssue.booking_id == booking_id, BardanaIssue.status == 'Active').scalar() or 0
    pending = required - issued
    return {'required': required, 'issued': issued, 'pending': pending}
