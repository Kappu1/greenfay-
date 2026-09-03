from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.database import get_db
from app.models import Farmer, Booking, SeedIssue, SeedPayment, BardanaIssue, DispatchLine, Commitment, AuditLog, Dispatch
from app.auth import current_user, audit, code

router = APIRouter()

def check_farmer_duplicates(db, name, mobile, village, exclude_id=None):
    q = db.query(Farmer).filter(Farmer.active == True)
    if exclude_id:
        q = q.filter(Farmer.id != exclude_id)
    candidates = q.filter(
        or_(
            Farmer.name.ilike(f'%{name.strip()}%'),
            Farmer.mobile == mobile if mobile else False
        )
    ).limit(5).all()
    return [{'id': f.id, 'name': f.name, 'village': f.village, 'mobile': f.mobile} for f in candidates]

@router.get('/farmers')
def list_farmers(q: str = '', village: str = '', active: bool = None, page: int = 1, per_page: int = 50, db: Session = Depends(get_db), user = Depends(current_user)):
    qry = db.query(Farmer)
    if active is not None:
        qry = qry.filter(Farmer.active == active)
    if village:
        qry = qry.filter(Farmer.village.ilike(f'%{village}%'))
    if q:
        qry = qry.filter(or_(Farmer.name.ilike(f'%{q}%'), Farmer.village.ilike(f'%{q}%'), Farmer.mobile.ilike(f'%{q}%'), Farmer.farmer_code.ilike(f'%{q}%')))
    
    total = qry.count()
    items = qry.order_by(Farmer.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    result = [{'id': f.id, 'farmer_code': f.farmer_code, 'name': f.name, 'relation_name': f.relation_name, 'mobile': f.mobile, 'village': f.village, 'address': f.address, 'active': f.active} for f in items]
    return {"items": result, "total": total, "page": page, "per_page": per_page, "pages": (total + per_page - 1) // per_page}

@router.post('/farmers')
async def create_farmer(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    name = data.get('name')
    mobile = data.get('mobile')
    village = data.get('village')
    
    if not name: raise HTTPException(400, 'Farmer name required')
    
    if not data.get('force'):
        dups = check_farmer_duplicates(db, name, mobile, village)
        if dups:
            return {"duplicate_warning": dups}

    f = Farmer(
        name=name.strip(),
        relation_name=data.get('relation_name'),
        relation_type=data.get('relation_type', 'Father'),
        mobile=mobile,
        alternate_mobile=data.get('alternate_mobile'),
        village=village,
        village_id=data.get('village_id'),
        address=data.get('address'),
        district=data.get('district'),
        state=data.get('state', 'Punjab'),
        remarks=data.get('remarks')
    )
    db.add(f)
    db.flush()
    f.farmer_code = code('FAR', f.id)
    audit(db, user, 'Farmer', f.id, 'CREATE', f.name)
    db.commit()
    return {'id': f.id, 'farmer_code': f.farmer_code}

@router.get('/farmers/{id}')
def farmer_detail(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    f = db.get(Farmer, id)
    if not f: raise HTTPException(404, 'Farmer not found')
    
    bookings = []
    for b in f.bookings:
        bookings.append({
            'id': b.id, 'booking_code': b.booking_code, 'season': b.season, 'agreement_no': b.agreement_no,
            'booking_type': b.booking_type, 'total_acres': b.total_acres, 'status': b.status,
            'varieties': [{'id': v.id, 'variety': v.variety, 'acres': v.acres, 'seed_type': v.seed_type} for v in b.varieties],
            'commitments': [{'id': c.id, 'month': c.contract_month, 'year': c.contract_year, 'variety': c.booking_variety.variety if c.booking_variety else None, 'contracted_bags': c.contracted_bags} for c in b.commitments]
        })
    return {'id': f.id, 'farmer_code': f.farmer_code, 'name': f.name, 'relation_name': f.relation_name, 'mobile': f.mobile, 'village': f.village, 'address': f.address, 'bookings': bookings}

@router.put('/farmers/{id}')
async def update_farmer(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    f = db.get(Farmer, id)
    if not f: raise HTTPException(404, 'Farmer not found')
    
    import json
    old_vals = {c.name: getattr(f, c.name) for c in f.__table__.columns if c.name not in ['created_at', 'updated_at']}
    
    for k, v in data.items():
        if hasattr(f, k):
            setattr(f, k, v)
    
    new_vals = {c.name: getattr(f, c.name) for c in f.__table__.columns if c.name not in ['created_at', 'updated_at']}
    db.flush()
    db.add(AuditLog(user_id=user.id, entity='Farmer', entity_id=f.id, action='UPDATE', details='Farmer updated', module='Farmers', old_values=json.dumps(old_vals, default=str), new_values=json.dumps(new_vals, default=str), user_name=user.name))
    db.commit()
    return {"ok": True}

@router.get('/farmers/{id}/summary')
def farmer_summary(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    f = db.get(Farmer, id)
    if not f: raise HTTPException(404, 'Farmer not found')
    
    total_bookings = len(f.bookings)
    total_acres = sum(b.total_acres for b in f.bookings if b.status != 'Cancelled')
    
    seed_issues = db.query(SeedIssue).filter(SeedIssue.farmer_id == id, SeedIssue.status == 'Active').all()
    seed_value = sum(i.total_value for i in seed_issues)
    
    seed_paid = db.query(func.sum(SeedPayment.amount)).filter(SeedPayment.farmer_id == id, SeedPayment.status == 'Active').scalar() or 0
    seed_balance = seed_value - seed_paid
    
    bardana_issued = db.query(func.sum(BardanaIssue.bags_issued)).filter(BardanaIssue.farmer_id == id, BardanaIssue.status == 'Active').scalar() or 0
    
    contract_bags = db.query(func.sum(Commitment.contracted_bags)).join(Booking).filter(Booking.farmer_id == id, Commitment.status != 'Cancelled').scalar() or 0
    potato_received = db.query(func.sum(DispatchLine.bags)).join(Dispatch).filter(DispatchLine.farmer_id == id, Dispatch.status == 'Finalized').scalar() or 0
    contract_pending = contract_bags - potato_received
    payment_status = 'Completed' if seed_balance <= 0 and seed_value > 0 else ('Excess' if seed_paid > seed_value > 0 else ('Partial' if seed_paid > 0 else ('Not Paid' if seed_value > 0 else 'No Dues')))
    
    return {
        "total_bookings": total_bookings, "total_acres": total_acres,
        "seed_value": seed_value, "seed_paid": seed_paid, "seed_balance": seed_balance,
        "bardana_issued": bardana_issued, "contract_bags": contract_bags,
        "potato_received": potato_received, "contract_pending": contract_pending,
        "payment_status": payment_status
    }

@router.get('/farmers/{id}/seed')
def farmer_seed(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    issues = db.query(SeedIssue).filter(SeedIssue.farmer_id == id).all()
    payments = db.query(SeedPayment).filter(SeedPayment.farmer_id == id).all()
    return {
        "issues": [{"id": i.id, "variety": i.variety, "issue_date": str(i.issue_date), "packets": i.packets, "total_value": i.total_value, "status": i.status} for i in issues],
        "payments": [{"id": p.id, "payment_date": str(p.payment_date), "amount": p.amount, "mode": p.mode, "status": p.status} for p in payments]
    }

@router.get('/farmers/{id}/bardana')
def farmer_bardana(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    bardana = db.query(BardanaIssue).filter(BardanaIssue.farmer_id == id).all()
    return [{"id": b.id, "issue_date": str(b.issue_date), "bags_issued": b.bags_issued, "contract_month": b.contract_month, "status": b.status} for b in bardana]

@router.get('/farmers/{id}/dispatches')
def farmer_dispatches(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    lines = db.query(DispatchLine).filter(DispatchLine.farmer_id == id).all()
    return [{"id": l.id, "dispatch_code": l.dispatch.dispatch_code, "dispatch_date": str(l.dispatch.dispatch_date), "variety": l.variety, "bags": l.bags, "status": l.dispatch.status} for l in lines]

@router.get('/farmers/{id}/audit')
def farmer_audit(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    logs = db.query(AuditLog).filter(AuditLog.entity == 'Farmer', AuditLog.entity_id == id).order_by(AuditLog.id.desc()).all()
    return [{"id": l.id, "action": l.action, "details": l.details, "created_at": str(l.created_at), "user_name": l.user_name} for l in logs]
