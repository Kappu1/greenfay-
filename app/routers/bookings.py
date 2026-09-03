from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Booking, Farmer, BookingVariety, Commitment, DispatchLine, Dispatch, Season
from app.auth import current_user, audit, code
from datetime import date, datetime

router = APIRouter()

@router.get('/bookings/seasons')
def list_unique_seasons(db: Session = Depends(get_db), user = Depends(current_user)):
    return [s.name for s in db.query(Season).filter(Season.active == True).order_by(Season.start_date.desc()).all()]

@router.get('/bookings')
def list_bookings(farmer_id: int = None, season: str = '', status: str = '', booking_type: str = '', db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(Booking)
    if farmer_id: q = q.filter(Booking.farmer_id == farmer_id)
    if season: q = q.filter(Booking.season == season)
    if status: q = q.filter(Booking.status == status)
    if booking_type: q = q.filter(Booking.booking_type == booking_type)
    
    rows = []
    for b in q.order_by(Booking.id.desc()).all():
        rows.append({'id': b.id, 'booking_code': b.booking_code, 'farmer_id': b.farmer_id, 'farmer': b.farmer.name if b.farmer else '', 'season': b.season, 'booking_date': str(b.booking_date), 'agreement_no': b.agreement_no, 'booking_type': b.booking_type, 'total_acres': b.total_acres, 'destination': b.destination, 'status': b.status})
    return rows

@router.post('/bookings')
async def create_booking(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    d = await request.json()
    farmer = db.get(Farmer, int(d.get('farmer_id', 0)))
    if not farmer: raise HTTPException(400, 'Valid farmer required')
    
    season = d.get('season', '2025-26')
    agreement_no = d.get('agreement_no')
    if agreement_no:
        existing = db.query(Booking).filter(Booking.season == season, Booking.agreement_no == agreement_no).first()
        warning = 'Duplicate agreement number in season' if existing else None
    else:
        warning = None

    varieties = d.get('varieties') or []
    commitments = d.get('commitments') or []
    
    b = Booking(
        farmer_id=farmer.id,
        season=season,
        season_id=d.get('season_id'),
        booking_date=date.fromisoformat(d.get('booking_date') or str(date.today())),
        agreement_no=agreement_no,
        receipt_no=d.get('receipt_no'),
        booking_type=d.get('booking_type', 'With Seed'),
        company_program=d.get('company_program', 'Green Fay Farm Foods'),
        total_acres=float(d.get('total_acres') or sum(float(x.get('acres', 0)) for x in varieties)),
        destination=d.get('destination'),
        destination_id=d.get('destination_id'),
        status=d.get('status', 'Active'),
        remarks=d.get('remarks'),
        created_by_id=user.id
    )
    db.add(b)
    db.flush()
    b.booking_code = code('BKG', b.id)
    
    vmap = {}
    for i, v in enumerate(varieties):
        obj = BookingVariety(
            booking_id=b.id,
            variety=v.get('variety'),
            variety_id=v.get('variety_id'),
            acres=float(v.get('acres', 0)),
            seed_type=v.get('seed_type', 'With Seed'),
            seed_source=v.get('seed_source'),
            supplier_id=v.get('supplier_id'),
            planned_seed_packets=float(v.get('planned_seed_packets', 0)),
            expected_buyback_qty=float(v.get('expected_buyback_qty', 0)),
            remarks=v.get('remarks')
        )
        db.add(obj)
        db.flush()
        vmap[i] = obj.id
        
    for c in commitments:
        vi = c.get('variety_index')
        vid = vmap.get(int(vi)) if vi is not None and str(vi).isdigit() else None
        db.add(Commitment(
            booking_id=b.id,
            booking_variety_id=vid,
            contract_month=c.get('contract_month'),
            contract_year=int(c.get('contract_year', date.today().year)),
            contracted_bags=float(c.get('contracted_bags', 0)),
            contracted_weight=float(c.get('contracted_weight', 0)),
            buyback_rate=float(c.get('buyback_rate', 0)),
            default_rate=float(c.get('default_rate', 0)),
            destination=c.get('destination') or b.destination,
            destination_id=c.get('destination_id') or b.destination_id,
            remarks=c.get('remarks')
        ))
    
    audit(db, user, 'Booking', b.id, 'CREATE', b.booking_code)
    db.commit()
    res = {'id': b.id, 'booking_code': b.booking_code}
    if warning: res['warning'] = warning
    return res

@router.get('/bookings/{id}')
def booking_detail(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    b = db.get(Booking, id)
    if not b: raise HTTPException(404, 'Booking not found')
    
    varieties = []
    for v in b.varieties:
        varieties.append({
            'id': v.id, 'variety': v.variety, 'variety_id': v.variety_id, 'acres': v.acres,
            'seed_type': v.seed_type, 'planned_seed_packets': v.planned_seed_packets,
            'expected_buyback_qty': v.expected_buyback_qty
        })
        
    commitments = []
    for c in b.commitments:
        received = db.query(func.sum(DispatchLine.bags)).join(Dispatch).filter(DispatchLine.commitment_id == c.id, Dispatch.status == 'Finalized').scalar() or 0
        pending = c.contracted_bags - received
        pct = (received / c.contracted_bags * 100) if c.contracted_bags > 0 else 0
        status = 'Completed' if pending <= 0 else ('In Progress' if received > 0 else 'Not Started')
        commitments.append({
            'id': c.id, 'variety': c.booking_variety.variety if c.booking_variety else '',
            'contract_month': c.contract_month, 'contract_year': c.contract_year,
            'contracted_bags': c.contracted_bags, 'received_bags': received,
            'pending_bags': pending, 'completion_pct': round(pct, 2), 'status': status
        })
        
    return {
        'id': b.id, 'booking_code': b.booking_code, 'farmer': {'id': b.farmer.id, 'name': b.farmer.name} if b.farmer else None,
        'season': b.season, 'status': b.status, 'varieties': varieties, 'commitments': commitments
    }

@router.put('/bookings/{id}')
async def update_booking_header(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    d = await request.json()
    b = db.get(Booking, id)
    if not b: raise HTTPException(404, 'Booking not found')
    
    for k, v in d.items():
        if hasattr(b, k) and k not in ['id', 'booking_code', 'farmer_id', 'created_at', 'created_by_id']:
            setattr(b, k, v)
    b.updated_by_id = user.id
    b.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}

@router.put('/bookings/{id}/status')
async def update_booking_status(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    d = await request.json()
    b = db.get(Booking, id)
    if not b: raise HTTPException(404, 'Booking not found')
    b.status = d.get('status', 'Active')
    b.updated_by_id = user.id
    b.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}

@router.get('/bookings/{id}/varieties')
def list_booking_varieties(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    b = db.get(Booking, id)
    if not b: raise HTTPException(404, 'Not found')
    return [{'id': v.id, 'variety': v.variety, 'variety_id': v.variety_id, 'acres': v.acres, 'seed_type': v.seed_type, 'planned_seed_packets': v.planned_seed_packets, 'expected_buyback_qty': v.expected_buyback_qty} for v in b.varieties]

@router.post('/bookings/{id}/varieties')
async def add_booking_variety(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    d = await request.json()
    b = db.get(Booking, id)
    if not b: raise HTTPException(404, 'Not found')
    v = BookingVariety(booking_id=b.id, **d)
    db.add(v)
    db.commit()
    db.refresh(v)
    return {'id': v.id}

@router.put('/bookings/{id}/varieties/{vid}')
async def update_booking_variety(id: int, vid: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    d = await request.json()
    v = db.get(BookingVariety, vid)
    if not v or v.booking_id != id: raise HTTPException(404, 'Not found')
    for k, val in d.items():
        if hasattr(v, k) and k not in ['id', 'booking_id']:
            setattr(v, k, val)
    db.commit()
    return {'ok': True}

@router.get('/bookings/{id}/commitments')
def list_booking_commitments(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    b = db.get(Booking, id)
    if not b: raise HTTPException(404, 'Not found')
    commitments = []
    for c in b.commitments:
        received = db.query(func.sum(DispatchLine.bags)).join(Dispatch).filter(DispatchLine.commitment_id == c.id, Dispatch.status == 'Finalized').scalar() or 0
        pending = c.contracted_bags - received
        pct = (received / c.contracted_bags * 100) if c.contracted_bags > 0 else 0
        status = 'Completed' if pending <= 0 else ('In Progress' if received > 0 else 'Not Started')
        commitments.append({
            'id': c.id, 'variety': c.booking_variety.variety if c.booking_variety else '',
            'contract_month': c.contract_month, 'contract_year': c.contract_year,
            'contracted_bags': c.contracted_bags, 'received_bags': received,
            'pending_bags': pending, 'completion_pct': round(pct, 2), 'status': status
        })
    return commitments

@router.post('/bookings/{id}/commitments')
async def add_booking_commitment(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    # allow single obj or list
    if not isinstance(data, list):
        data = [data]
    b = db.get(Booking, id)
    if not b: raise HTTPException(404, 'Not found')
    ids = []
    for d in data:
        c = Commitment(booking_id=b.id, **d)
        db.add(c)
        db.flush()
        ids.append(c.id)
    db.commit()
    return {'ids': ids}

@router.put('/bookings/{id}/commitments/{cid}')
async def update_booking_commitment(id: int, cid: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    d = await request.json()
    c = db.get(Commitment, cid)
    if not c or c.booking_id != id: raise HTTPException(404, 'Not found')
    for k, val in d.items():
        if hasattr(c, k) and k not in ['id', 'booking_id']:
            setattr(c, k, val)
    db.commit()
    return {'ok': True}
