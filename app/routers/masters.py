from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models import (Season, Village, Variety, Destination, Supplier, SeedRateMaster, BuybackRateMaster,
                        BardanaType, Transporter, TaxRate)
from app.auth import current_user, audit
from datetime import date

router = APIRouter()

@router.get('/seasons')
def list_seasons(active: bool = None, db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(Season)
    if active is not None:
        q = q.filter(Season.active == active)
    return q.order_by(Season.start_date.desc()).all()

def parse_date(v):
    if isinstance(v, str) and v.strip():
        return date.fromisoformat(v.strip())
    return v if isinstance(v, date) else None

@router.post('/seasons')
async def create_season(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    if not data.get('name'): raise HTTPException(400, 'Name required')
    if data.get('start_date'): data['start_date'] = parse_date(data['start_date'])
    if data.get('end_date'): data['end_date'] = parse_date(data['end_date'])
    if data.get('start_date') and data.get('end_date') and data['start_date'] > data['end_date']:
        raise HTTPException(400, 'Start date must be before end date')
    if db.query(Season).filter(Season.name == data['name']).first():
        raise HTTPException(400, 'Season already exists')
    obj = Season(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    audit(db, user, 'Season', obj.id, 'CREATE', obj.name)
    return obj

@router.put('/seasons/{id}')
async def update_season(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    obj = db.get(Season, id)
    if not obj: raise HTTPException(404, 'Not found')
    if 'start_date' in data: data['start_date'] = parse_date(data['start_date'])
    if 'end_date' in data: data['end_date'] = parse_date(data['end_date'])
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    audit(db, user, 'Season', obj.id, 'UPDATE', obj.name)
    return obj

@router.delete('/seasons/{id}')
def delete_season(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    obj = db.get(Season, id)
    if not obj: raise HTTPException(404, 'Not found')
    db.delete(obj)
    db.commit()
    audit(db, user, 'Season', id, 'DELETE', obj.name)
    return {'ok': True}

# Villages
@router.get('/villages')
def list_villages(active: bool = None, db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(Village)
    if active is not None:
        q = q.filter(Village.active == active)
    return [{'id': v.id, 'village_name': v.village_name, 'district': v.district, 'state': v.state, 'active': v.active} for v in q.order_by(Village.village_name).all()]

@router.post('/villages')
async def create_village(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    if not data.get('village_name'): raise HTTPException(400, 'Name required')
    # case-insensitive check
    existing = db.query(Village).filter(Village.village_name.ilike(data['village_name'])).first()
    if existing and existing.district == data.get('district') and existing.state == data.get('state'):
         return {'warning': 'Duplicate village detected', 'id': existing.id}
    obj = Village(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    audit(db, user, 'Village', obj.id, 'CREATE', obj.village_name)
    return {'id': obj.id, 'village_name': obj.village_name, 'district': obj.district, 'state': obj.state, 'active': obj.active}

@router.put('/villages/{id}')
async def update_village(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    obj = db.get(Village, id)
    if not obj: raise HTTPException(404, 'Not found')
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    audit(db, user, 'Village', obj.id, 'UPDATE', obj.village_name)
    return obj

@router.delete('/villages/{id}')
def delete_village(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    obj = db.get(Village, id)
    if not obj: raise HTTPException(404, 'Not found')
    db.delete(obj)
    db.commit()
    audit(db, user, 'Village', id, 'DELETE', obj.village_name)
    return {'ok': True}

# Varieties
@router.get('/varieties')
def list_varieties(active: bool = None, db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(Variety)
    if active is not None:
        q = q.filter(Variety.active == active)
    return [{'id': v.id, 'name': v.name, 'code': v.code, 'active': v.active, 'default_seed_packets_per_acre': v.default_seed_packets_per_acre, 'default_buyback_bags_per_acre': v.default_buyback_bags_per_acre} for v in q.order_by(Variety.name).all()]

@router.post('/varieties')
async def create_variety(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    if not data.get('name') or not data.get('code'): raise HTTPException(400, 'Name and code required')
    obj = Variety(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    audit(db, user, 'Variety', obj.id, 'CREATE', obj.name)
    return {'id': obj.id, 'name': obj.name, 'code': obj.code, 'active': obj.active, 'default_seed_packets_per_acre': obj.default_seed_packets_per_acre, 'default_buyback_bags_per_acre': obj.default_buyback_bags_per_acre}

@router.put('/varieties/{id}')
async def update_variety(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    obj = db.get(Variety, id)
    if not obj: raise HTTPException(404, 'Not found')
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    audit(db, user, 'Variety', obj.id, 'UPDATE', obj.name)
    return obj

@router.delete('/varieties/{id}')
def delete_variety(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    obj = db.get(Variety, id)
    if not obj: raise HTTPException(404, 'Not found')
    db.delete(obj)
    db.commit()
    audit(db, user, 'Variety', id, 'DELETE', obj.name)
    return {'ok': True}

# Destinations
@router.get('/destinations')
def list_destinations(active: bool = None, db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(Destination)
    if active is not None:
        q = q.filter(Destination.active == active)
    return q.order_by(Destination.name).all()

@router.post('/destinations')
async def create_destination(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    obj = Destination(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    audit(db, user, 'Destination', obj.id, 'CREATE', obj.name)
    return obj

@router.put('/destinations/{id}')
async def update_destination(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    obj = db.get(Destination, id)
    if not obj: raise HTTPException(404, 'Not found')
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    audit(db, user, 'Destination', obj.id, 'UPDATE', obj.name)
    return obj

@router.delete('/destinations/{id}')
def delete_destination(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    obj = db.get(Destination, id)
    if not obj: raise HTTPException(404, 'Not found')
    db.delete(obj)
    db.commit()
    return {'ok': True}

# Suppliers
@router.get('/suppliers')
def list_suppliers(active: bool = None, db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(Supplier)
    if active is not None:
        q = q.filter(Supplier.active == active)
    return q.order_by(Supplier.supplier_name).all()

@router.post('/suppliers')
async def create_supplier(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    obj = Supplier(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    audit(db, user, 'Supplier', obj.id, 'CREATE', obj.supplier_name)
    return obj

@router.put('/suppliers/{id}')
async def update_supplier(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    obj = db.get(Supplier, id)
    if not obj: raise HTTPException(404, 'Not found')
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    return obj

@router.delete('/suppliers/{id}')
def delete_supplier(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    obj = db.get(Supplier, id)
    if not obj: raise HTTPException(404, 'Not found')
    db.delete(obj)
    db.commit()
    return {'ok': True}

# Seed Rate Master
@router.get('/seed-rates')
def list_seed_rates(active: bool = None, db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(SeedRateMaster)
    if active is not None:
        q = q.filter(SeedRateMaster.active == active)
    res = []
    for r in q.all():
        d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        d['variety_name'] = r.variety.name if r.variety else None
        d['season_name'] = r.season.name if r.season else None
        res.append(d)
    return res

@router.get('/seed-rates/lookup')
def lookup_seed_rate(variety_id: int, season_id: int, dt: date = None, db: Session = Depends(get_db), user = Depends(current_user)):
    if dt is None: dt = date.today()
    q = db.query(SeedRateMaster).filter(
        SeedRateMaster.variety_id == variety_id,
        SeedRateMaster.season_id == season_id,
        SeedRateMaster.active == True,
        SeedRateMaster.effective_from <= dt,
        or_(SeedRateMaster.effective_to == None, SeedRateMaster.effective_to >= dt)
    ).order_by(SeedRateMaster.effective_from.desc()).first()
    if not q: return None
    return {'rate_per_packet': q.rate_per_packet, 'packet_weight_kg': q.packet_weight_kg, 'id': q.id}

@router.post('/seed-rates')
async def create_seed_rate(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    if 'effective_from' in data: data['effective_from'] = parse_date(data['effective_from'])
    if 'effective_to' in data: data['effective_to'] = parse_date(data['effective_to'])
    obj = SeedRateMaster(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    audit(db, user, 'SeedRateMaster', obj.id, 'CREATE', str(obj.rate_per_packet))
    return obj

@router.put('/seed-rates/{id}')
async def update_seed_rate(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    obj = db.get(SeedRateMaster, id)
    if not obj: raise HTTPException(404, 'Not found')
    if 'effective_from' in data: data['effective_from'] = parse_date(data['effective_from'])
    if 'effective_to' in data: data['effective_to'] = parse_date(data['effective_to'])
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    return obj

@router.delete('/seed-rates/{id}')
def delete_seed_rate(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    obj = db.get(SeedRateMaster, id)
    if not obj: raise HTTPException(404, 'Not found')
    db.delete(obj)
    db.commit()
    return {'ok': True}

# Buyback Rate Master
@router.get('/buyback-rates')
def list_buyback_rates(active: bool = None, db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(BuybackRateMaster)
    if active is not None:
        q = q.filter(BuybackRateMaster.active == active)
    res = []
    for r in q.all():
        d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        d['variety_name'] = r.variety.name if r.variety else None
        d['season_name'] = r.season.name if r.season else None
        d['destination_name'] = r.destination.name if r.destination else None
        res.append(d)
    return res

@router.get('/buyback-rates/lookup')
def lookup_buyback_rate(season_id: int, contract_month: str, variety_id: int = None, destination_id: int = None, dt: date = None, db: Session = Depends(get_db), user = Depends(current_user)):
    if dt is None: dt = date.today()
    q = db.query(BuybackRateMaster).filter(
        BuybackRateMaster.season_id == season_id,
        BuybackRateMaster.contract_month == contract_month,
        BuybackRateMaster.active == True,
        BuybackRateMaster.effective_from <= dt,
        or_(BuybackRateMaster.effective_to == None, BuybackRateMaster.effective_to >= dt)
    )
    if variety_id: q = q.filter(or_(BuybackRateMaster.variety_id == variety_id, BuybackRateMaster.variety_id == None))
    if destination_id: q = q.filter(or_(BuybackRateMaster.destination_id == destination_id, BuybackRateMaster.destination_id == None))
    # Order by specificity
    res = q.order_by(BuybackRateMaster.variety_id.desc(), BuybackRateMaster.destination_id.desc(), BuybackRateMaster.effective_from.desc()).first()
    if not res: return None
    return {'rate_per_bag': res.rate_per_bag, 'id': res.id}

@router.post('/buyback-rates')
async def create_buyback_rate(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    if 'effective_from' in data: data['effective_from'] = parse_date(data['effective_from'])
    if 'effective_to' in data: data['effective_to'] = parse_date(data['effective_to'])
    obj = BuybackRateMaster(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    audit(db, user, 'BuybackRateMaster', obj.id, 'CREATE', str(obj.rate_per_bag))
    return obj

@router.put('/buyback-rates/{id}')
async def update_buyback_rate(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    obj = db.get(BuybackRateMaster, id)
    if not obj: raise HTTPException(404, 'Not found')
    if 'effective_from' in data: data['effective_from'] = parse_date(data['effective_from'])
    if 'effective_to' in data: data['effective_to'] = parse_date(data['effective_to'])
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    return obj

@router.delete('/buyback-rates/{id}')
def delete_buyback_rate(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    obj = db.get(BuybackRateMaster, id)
    if not obj: raise HTTPException(404, 'Not found')
    db.delete(obj)
    db.commit()
    return {'ok': True}

# Bardana Types
@router.get('/bardana-types')
def list_bardana_types(active: bool = None, db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(BardanaType)
    if active is not None:
        q = q.filter(BardanaType.active == active)
    return q.order_by(BardanaType.name).all()

@router.post('/bardana-types')
async def create_bardana_type(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    obj = BardanaType(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.put('/bardana-types/{id}')
async def update_bardana_type(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    obj = db.get(BardanaType, id)
    if not obj: raise HTTPException(404, 'Not found')
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    return obj

@router.delete('/bardana-types/{id}')
def delete_bardana_type(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    obj = db.get(BardanaType, id)
    if not obj: raise HTTPException(404, 'Not found')
    db.delete(obj)
    db.commit()
    return {'ok': True}

# Transporters
@router.get('/transporters')
def list_transporters(active: bool = None, db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(Transporter)
    if active is not None:
        q = q.filter(Transporter.active == active)
    return q.order_by(Transporter.transporter_name).all()

@router.post('/transporters')
async def create_transporter(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    obj = Transporter(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.put('/transporters/{id}')
async def update_transporter(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    obj = db.get(Transporter, id)
    if not obj: raise HTTPException(404, 'Not found')
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    return obj

@router.delete('/transporters/{id}')
def delete_transporter(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    obj = db.get(Transporter, id)
    if not obj: raise HTTPException(404, 'Not found')
    db.delete(obj)
    db.commit()
    return {'ok': True}

# Tax Rates
@router.get('/tax-rates')
def get_tax_rates(active: bool = None, db: Session = Depends(get_db), user = Depends(current_user)):
    q = db.query(TaxRate)
    if active is not None:
        q = q.filter(TaxRate.active == active)
    return q.order_by(TaxRate.effective_from.desc()).all()

@router.get('/tax-rates/for-date')
def tax_rates_for_date(date: str = '', dt: str = '', db: Session = Depends(get_db), user = Depends(current_user)):
    target_dt = date or dt
    d_obj = parse_date(target_dt) if target_dt else datetime.today().date()
    q = db.query(TaxRate).filter(
        TaxRate.active == True,
        TaxRate.effective_from <= d_obj,
        or_(TaxRate.effective_to == None, TaxRate.effective_to >= d_obj)
    ).order_by(TaxRate.effective_from.desc()).first()
    return q

@router.post('/tax-rates')
async def create_tax_rate(request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    if 'effective_from' in data: data['effective_from'] = parse_date(data['effective_from'])
    if 'effective_to' in data: data['effective_to'] = parse_date(data['effective_to'])
    obj = TaxRate(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.put('/tax-rates/{id}')
async def update_tax_rate(id: int, request: Request, db: Session = Depends(get_db), user = Depends(current_user)):
    data = await request.json()
    obj = db.get(TaxRate, id)
    if not obj: raise HTTPException(404, 'Not found')
    if 'effective_from' in data: data['effective_from'] = parse_date(data['effective_from'])
    if 'effective_to' in data: data['effective_to'] = parse_date(data['effective_to'])
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    return obj

@router.delete('/tax-rates/{id}')
def delete_tax_rate(id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    obj = db.get(TaxRate, id)
    if not obj: raise HTTPException(404, 'Not found')
    db.delete(obj)
    db.commit()
    return {'ok': True}
