from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.database import get_db
from app.models import Dispatch, DispatchLine, TaxRate, Farmer, Commitment, BookingVariety
from app.auth import current_user, audit, code
from datetime import date, datetime

router = APIRouter()

def tax_rate_for(db, dt):
    return db.query(TaxRate).filter(
        TaxRate.active == True,
        TaxRate.effective_from <= dt,
        or_(TaxRate.effective_to == None, TaxRate.effective_to >= dt)
    ).order_by(TaxRate.effective_from.desc()).first()

def calculate_tax(mandi_weight_kg: float, tax_rate: TaxRate) -> dict:
    if not tax_rate: return {'mandi_tax': 0, 'vikas_sulk': 0, 'taxable_quintals': 0, 'applied_mandi_rate': 0, 'applied_vikas_rate': 0, 'applied_mandi_cap': None, 'applied_vikas_cap': None, 'tax_rate_id': None}
    qtl = mandi_weight_kg / 100
    mandi_raw = qtl * tax_rate.mandi_rate_per_qtl
    vikas_raw = qtl * tax_rate.vikas_rate_per_qtl
    mandi_tax = min(mandi_raw, tax_rate.mandi_cap) if tax_rate.mandi_cap else mandi_raw
    vikas_sulk = min(vikas_raw, tax_rate.vikas_cap) if tax_rate.vikas_cap else vikas_raw
    return {
        'mandi_tax': round(mandi_tax, 2),
        'vikas_sulk': round(vikas_sulk, 2),
        'taxable_quintals': round(qtl, 3),
        'applied_mandi_rate': tax_rate.mandi_rate_per_qtl,
        'applied_vikas_rate': tax_rate.vikas_rate_per_qtl,
        'applied_mandi_cap': tax_rate.mandi_cap,
        'applied_vikas_cap': tax_rate.vikas_cap,
        'tax_rate_id': tax_rate.id
    }

@router.get('/dispatches')
def list_dispatches(date_from: str = '', date_to: str = '', truck_no: str = '', destination: str = '', status: str = '', transporter_id: int = None, farmer_id: int = None, db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(Dispatch)
    if date_from: q = q.filter(Dispatch.dispatch_date >= date.fromisoformat(date_from))
    if date_to: q = q.filter(Dispatch.dispatch_date <= date.fromisoformat(date_to))
    if truck_no: q = q.filter(Dispatch.truck_no.ilike(f'%{truck_no}%'))
    if destination: q = q.filter(Dispatch.destination.ilike(f'%{destination}%'))
    if status: q = q.filter(Dispatch.status == status)
    if transporter_id: q = q.filter(Dispatch.transporter_id == transporter_id)
    if farmer_id: q = q.join(Dispatch.lines).filter(DispatchLine.farmer_id == farmer_id).distinct()
    
    out = []
    for d in q.order_by(Dispatch.id.desc()).all():
        out.append({
            'id': d.id, 'dispatch_code': d.dispatch_code, 'date': str(d.dispatch_date),
            'truck_no': d.truck_no, 'destination': d.destination, 'gatepass_no': d.gatepass_no,
            'actual_weight_kg': d.actual_weight_kg, 'mandi_weight_kg': d.mandi_weight_kg,
            'mandi_tax': d.mandi_tax, 'vikas_sulk': d.vikas_sulk, 'status': d.status,
            'lines': [{'farmer': db.get(Farmer, l.farmer_id).name if l.farmer_id else '', 'variety': l.variety, 'bags': l.bags, 'weight_kg': l.weight_kg, 'commitment_id': l.commitment_id} for l in d.lines if l.status != 'Cancelled']
        })
    return out

@router.post('/dispatches')
async def create_dispatch(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    x = await request.json()
    dt = date.fromisoformat(x.get('dispatch_date') or str(date.today()))
    tr = tax_rate_for(db, dt)
    if not tr: raise HTTPException(400, 'No tax rate configured for dispatch date')
    
    mandi_weight = float(x.get('mandi_weight_kg') or x.get('actual_weight_kg') or 0)
    tax_res = calculate_tax(mandi_weight, tr)
    
    d = Dispatch(
        dispatch_date=dt,
        truck_no=x.get('truck_no'),
        transporter=x.get('transporter'),
        transporter_id=x.get('transporter_id'),
        destination=x.get('destination'),
        destination_id=x.get('destination_id'),
        gatepass_no=x.get('gatepass_no'),
        nine_r_no=x.get('nine_r_no'),
        actual_weight_kg=float(x.get('actual_weight_kg', 0)),
        mandi_weight_kg=mandi_weight,
        mandi_rate=tax_res['applied_mandi_rate'],
        vikas_rate=tax_res['applied_vikas_rate'],
        mandi_cap=tax_res['applied_mandi_cap'],
        vikas_cap=tax_res['applied_vikas_cap'],
        mandi_tax=tax_res['mandi_tax'],
        vikas_sulk=tax_res['vikas_sulk'],
        tax_rate_id=tax_res['tax_rate_id'],
        remarks=x.get('remarks'),
        created_by_id=user.id,
        status='Draft'
    )
    db.add(d)
    db.flush()
    d.dispatch_code = code('DSP', d.id)
    
    for l in x.get('lines', []):
        db.add(DispatchLine(
            dispatch_id=d.id,
            farmer_id=int(l['farmer_id']),
            booking_id=int(l['booking_id']),
            commitment_id=int(l['commitment_id']) if l.get('commitment_id') else None,
            variety=l['variety'],
            variety_id=l.get('variety_id'),
            bags=float(l.get('bags', 0)),
            weight_kg=float(l.get('weight_kg', 0)),
            remarks=l.get('remarks'),
            status='Active'
        ))
        
    audit(db, user, 'Dispatch', d.id, 'CREATE', d.dispatch_code)
    db.commit()
    return {'id': d.id, 'dispatch_code': d.dispatch_code, 'mandi_tax': d.mandi_tax, 'vikas_sulk': d.vikas_sulk, 'status': d.status}

@router.get('/dispatches/{id}')
def get_dispatch(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    d = db.get(Dispatch, id)
    if not d: raise HTTPException(404, 'Not found')
    lines = []
    for l in d.lines:
        lines.append({
            'id': l.id, 'farmer_id': l.farmer_id, 'farmer': db.get(Farmer, l.farmer_id).name if l.farmer_id else '',
            'booking_id': l.booking_id, 'commitment_id': l.commitment_id, 'variety': l.variety,
            'bags': l.bags, 'weight_kg': l.weight_kg, 'status': l.status
        })
    return {
        'id': d.id, 'dispatch_code': d.dispatch_code, 'dispatch_date': str(d.dispatch_date),
        'truck_no': d.truck_no, 'transporter': d.transporter, 'destination': d.destination,
        'gatepass_no': d.gatepass_no, 'nine_r_no': d.nine_r_no, 'actual_weight_kg': d.actual_weight_kg,
        'mandi_weight_kg': d.mandi_weight_kg, 'mandi_tax': d.mandi_tax, 'vikas_sulk': d.vikas_sulk,
        'status': d.status, 'remarks': d.remarks, 'lines': lines
    }

@router.put('/dispatches/{id}')
async def update_dispatch(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    d = await request.json()
    obj = db.get(Dispatch, id)
    if not obj: raise HTTPException(404, 'Not found')
    if obj.status != 'Draft': raise HTTPException(400, 'Can only edit draft dispatches')
    
    for k, v in d.items():
        if hasattr(obj, k) and k not in ['id', 'dispatch_code', 'created_at', 'created_by_id', 'status', 'mandi_tax', 'vikas_sulk']:
            if k == 'dispatch_date': v = date.fromisoformat(v)
            setattr(obj, k, v)
    
    # Recalculate tax just in case date/weight changed
    tr = tax_rate_for(db, obj.dispatch_date)
    if tr:
        tax_res = calculate_tax(obj.mandi_weight_kg, tr)
        obj.mandi_tax = tax_res['mandi_tax']
        obj.vikas_sulk = tax_res['vikas_sulk']
        obj.mandi_rate = tax_res['applied_mandi_rate']
        obj.vikas_rate = tax_res['applied_vikas_rate']
        obj.mandi_cap = tax_res['applied_mandi_cap']
        obj.vikas_cap = tax_res['applied_vikas_cap']
        obj.tax_rate_id = tax_res['tax_rate_id']
        
    db.commit()
    return {'ok': True}

@router.post('/dispatches/{id}/lines')
async def add_dispatch_line(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    d = db.get(Dispatch, id)
    if not d: raise HTTPException(404, 'Not found')
    if d.status != 'Draft': raise HTTPException(400, 'Can only edit draft dispatches')
    
    l_data = await request.json()
    l = DispatchLine(
        dispatch_id=d.id,
        farmer_id=int(l_data['farmer_id']),
        booking_id=int(l_data['booking_id']),
        commitment_id=int(l_data['commitment_id']) if l_data.get('commitment_id') else None,
        variety=l_data['variety'],
        variety_id=l_data.get('variety_id'),
        bags=float(l_data.get('bags', 0)),
        weight_kg=float(l_data.get('weight_kg', 0)),
        remarks=l_data.get('remarks'),
        status='Active'
    )
    db.add(l)
    db.commit()
    db.refresh(l)
    return {'id': l.id}

@router.delete('/dispatches/{id}/lines/{line_id}')
def delete_dispatch_line(id: int, line_id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    d = db.get(Dispatch, id)
    if not d: raise HTTPException(404, 'Dispatch not found')
    if d.status != 'Draft': raise HTTPException(400, 'Can only edit draft dispatches')
    
    l = db.get(DispatchLine, line_id)
    if not l or l.dispatch_id != id: raise HTTPException(404, 'Line not found')
    
    db.delete(l)
    db.commit()
    return {'ok': True}

@router.post('/dispatches/{id}/finalize')
def finalize_dispatch(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    d = db.get(Dispatch, id)
    if not d: raise HTTPException(404, 'Not found')
    if d.status != 'Draft': raise HTTPException(400, 'Only draft can be finalized')
    
    tr = tax_rate_for(db, d.dispatch_date)
    if tr:
        tax_res = calculate_tax(d.mandi_weight_kg, tr)
        d.mandi_tax = tax_res['mandi_tax']
        d.vikas_sulk = tax_res['vikas_sulk']
        d.mandi_rate = tax_res['applied_mandi_rate']
        d.vikas_rate = tax_res['applied_vikas_rate']
        d.mandi_cap = tax_res['applied_mandi_cap']
        d.vikas_cap = tax_res['applied_vikas_cap']
        d.tax_rate_id = tax_res['tax_rate_id']
        
    d.status = 'Finalized'
    audit(db, user, 'Dispatch', d.id, 'FINALIZE', d.dispatch_code)
    db.commit()
    return {'ok': True, 'status': d.status}

@router.post('/dispatches/{id}/cancel')
async def cancel_dispatch(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    d = db.get(Dispatch, id)
    if not d: raise HTTPException(404, 'Not found')
    
    d.status = 'Cancelled'
    d.cancelled_by_id = user.id
    d.cancelled_at = datetime.utcnow()
    d.cancellation_reason = data.get('reason')
    
    # Also cancel lines so they don't count toward commitment progress
    for l in d.lines:
        l.status = 'Cancelled'
        
    audit(db, user, 'Dispatch', d.id, 'CANCEL', d.dispatch_code)
    db.commit()
    return {'ok': True}

@router.get('/contracts/due')
def contracts_due(month: str = '', variety: str = '', farmer: str = '', destination: str = '', season: str = '', status: str = '', seed_type: str = '', db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(Commitment).join(Commitment.booking)
    if month: q = q.filter(Commitment.contract_month == month)
    if season: q = q.filter(Booking.season == season)
    if destination: q = q.filter(Commitment.destination == destination)
    
    res = []
    for c in q.order_by(Commitment.contract_year, Commitment.id).all():
        b = c.booking
        if not b or not b.farmer: continue
        if farmer and farmer.lower() not in b.farmer.name.lower(): continue
        
        variety_name = c.booking_variety.variety if c.booking_variety else ''
        if variety and variety.lower() not in variety_name.lower(): continue
        
        c_seed_type = c.booking_variety.seed_type if c.booking_variety else ''
        if seed_type and seed_type.lower() != c_seed_type.lower(): continue
        
        received = db.query(func.sum(DispatchLine.bags)).join(Dispatch).filter(DispatchLine.commitment_id == c.id, Dispatch.status == 'Finalized').scalar() or 0
        pending = c.contracted_bags - received
        pct = (received / c.contracted_bags * 100) if c.contracted_bags > 0 else 0
        c_status = 'Completed' if pending <= 0 else ('In Progress' if received > 0 else 'Not Started')
        
        if status and status != c_status: continue
        
        res.append({
            "id": c.id,
            "farmer": b.farmer.name,
            "farmer_id": b.farmer.id,
            "village": b.farmer.village,
            "booking": b.booking_code,
            "booking_id": b.id,
            "agreement_no": b.agreement_no,
            "variety": variety_name,
            "contract_month": c.contract_month,
            "contract_year": c.contract_year,
            "destination": c.destination,
            "contracted_bags": c.contracted_bags,
            "received_bags": received,
            "pending_bags": pending,
            "completion_pct": round(pct, 2),
            "status": c_status,
            "seed_type": c_seed_type
        })
    return res
