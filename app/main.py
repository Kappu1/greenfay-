from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import date, datetime, timedelta
import os, json, csv, io

from .database import init_db, get_db, SessionLocal
from .models import *
from .routers import masters, farmers, bookings, seed, bardana, dispatch, reports
from .auth import pw_hash, pw_verify, sign_token, parse_token, current_user, audit, code

app = FastAPI(title='Green Fay Contract Farming Platform')
app.mount('/static', StaticFiles(directory='app/static'), name='static')
templates = Jinja2Templates(directory='app/templates')

MONTH_ORDER = ['January','February','March','April','May','June','July','August','September','October','November','December']

# Include routers
app.include_router(masters.router, prefix='/api/masters', tags=['masters'])
app.include_router(farmers.router, prefix='/api', tags=['farmers'])
app.include_router(bookings.router, prefix='/api', tags=['bookings'])
app.include_router(seed.router, prefix='/api/seed', tags=['seed'])
app.include_router(bardana.router, prefix='/api', tags=['bardana'])
app.include_router(dispatch.router, prefix='/api', tags=['dispatch'])
app.include_router(reports.router, prefix='/api/reports', tags=['reports'])

def seed_data():
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add(User(email='admin@greenfay.local', name='GreenFay Admin', role='admin', password_hash=pw_hash('admin123')))
        if db.query(TaxRate).count() == 0:
            db.add_all([
                TaxRate(effective_from=date(2025,1,1), effective_to=date(2025,6,30), mandi_rate_per_qtl=6, vikas_rate_per_qtl=3, mandi_cap=2400, vikas_cap=1200),
                TaxRate(effective_from=date(2025,7,1), effective_to=None, mandi_rate_per_qtl=5, vikas_rate_per_qtl=2.5, mandi_cap=2000, vikas_cap=1000),
            ])
        db.commit()
        
        # Phase 2 master data
        if db.query(Season).count() == 0:
            db.add(Season(name='2025-26', start_date=date(2025,4,1), end_date=date(2026,3,31), active=True))
        if db.query(Variety).count() == 0:
            varieties = [
                Variety(name='LR', code='LR', default_seed_packets_per_acre=25, default_buyback_bags_per_acre=250),
                Variety(name='Fry Sona', code='FRYSONA', default_seed_packets_per_acre=25, default_buyback_bags_per_acre=250),
                Variety(name='Chipsona', code='CHIPS', default_seed_packets_per_acre=25, default_buyback_bags_per_acre=250),
                Variety(name='CH-3', code='CH3', default_seed_packets_per_acre=25, default_buyback_bags_per_acre=250),
                Variety(name='TB32', code='TB32', default_seed_packets_per_acre=25, default_buyback_bags_per_acre=250),
                Variety(name='Santana', code='SANT', default_seed_packets_per_acre=25, default_buyback_bags_per_acre=250),
                Variety(name='Innovator', code='INNOV', default_seed_packets_per_acre=25, default_buyback_bags_per_acre=250),
                Variety(name='GF1', code='GF1', default_seed_packets_per_acre=25, default_buyback_bags_per_acre=250),
            ]
            db.add_all(varieties)
        if db.query(Destination).count() == 0:
            db.add_all([Destination(name='Plant'), Destination(name='Cold Store')])
        if db.query(Supplier).count() == 0:
            db.add(Supplier(supplier_name='Green Fay Farm Foods'))
        if db.query(BardanaType).count() == 0:
            db.add(BardanaType(name='Potato Storage Bag', bag_capacity=50))
        if db.query(Village).count() == 0:
            db.add(Village(village_name='Khakhra Khurd', district='Hoshiarpur', state='Punjab'))
        db.commit()

        if db.query(Farmer).count() == 0:
            f = Farmer(name='Gurpreet Singh', relation_name='Baldev Singh', village='Khakhra Khurd', mobile='9876543210', address='Khakhra Khurd, Punjab')
            db.add(f); db.flush(); f.farmer_code = code('FAR', f.id)
            b = Booking(farmer_id=f.id, season='2025-26', booking_date=date(2025,10,1), agreement_no='GF-DEMO-001', booking_type='Mixed', total_acres=7, destination='Plant')
            db.add(b); db.flush(); b.booking_code=code('BKG',b.id)
            v1=BookingVariety(booking_id=b.id,variety='LR',acres=2,seed_type='With Seed',seed_source='Green Fay Farm Foods',planned_seed_packets=50,expected_buyback_qty=500)
            v2=BookingVariety(booking_id=b.id,variety='Fry Sona',acres=3,seed_type='With Seed',seed_source='Green Fay Farm Foods',planned_seed_packets=75,expected_buyback_qty=700)
            v3=BookingVariety(booking_id=b.id,variety='CH-3',acres=2,seed_type='Without Seed',expected_buyback_qty=400)
            db.add_all([v1,v2,v3]); db.flush()
            db.add_all([
                Commitment(booking_id=b.id,booking_variety_id=v1.id,contract_month='January',contract_year=2026,contracted_bags=500,buyback_rate=0,destination='Plant'),
                Commitment(booking_id=b.id,booking_variety_id=v2.id,contract_month='February',contract_year=2026,contracted_bags=700,buyback_rate=0,destination='Cold Store'),
                Commitment(booking_id=b.id,booking_variety_id=v3.id,contract_month='March',contract_year=2026,contracted_bags=400,buyback_rate=0,destination='Plant'),
            ])
            db.commit()
    finally: db.close()

@app.on_event('startup')
def startup():
    init_db()
    seed_data()

@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    return FileResponse('app/templates/index.html', media_type='text/html')

@app.post('/api/login')
async def login(request: Request, response: Response, db: Session=Depends(get_db)):
    data=await request.json(); u=db.query(User).filter(User.email==data.get('email')).first()
    if not u or not pw_verify(data.get('password',''),u.password_hash): raise HTTPException(401,'Invalid email or password')
    response=JSONResponse({'ok':True,'user':{'id':u.id,'name':u.name,'role':u.role}})
    response.set_cookie('gf_session',sign_token(u.id),httponly=True,samesite='lax',max_age=604800)
    return response

@app.post('/api/logout')
def logout():
    r=JSONResponse({'ok':True}); r.delete_cookie('gf_session'); return r

@app.get('/api/me')
def me(user:User=Depends(current_user)): return {'id':user.id,'name':user.name,'email':user.email,'role':user.role}

@app.get('/api/dashboard')
def dashboard(db:Session=Depends(get_db), user:User=Depends(current_user)):
    total_farmers=db.query(Farmer).count(); total_bookings=db.query(Booking).count()
    acres=db.query(func.coalesce(func.sum(Booking.total_acres),0)).scalar() or 0
    with_seed=db.query(func.coalesce(func.sum(BookingVariety.acres),0)).filter(BookingVariety.seed_type=='With Seed').scalar() or 0
    without_seed=db.query(func.coalesce(func.sum(BookingVariety.acres),0)).filter(BookingVariety.seed_type=='Without Seed').scalar() or 0
    contracted=db.query(func.coalesce(func.sum(Commitment.contracted_bags),0)).scalar() or 0
    delivered=db.query(func.coalesce(func.sum(DispatchLine.bags),0)).scalar() or 0
    seed_value=db.query(func.coalesce(func.sum(SeedIssue.total_value),0)).scalar() or 0
    paid=db.query(func.coalesce(func.sum(SeedPayment.amount),0)).scalar() or 0
    bardana=db.query(func.coalesce(func.sum(BardanaIssue.bags_issued),0)).scalar() or 0
    mandi=db.query(func.coalesce(func.sum(Dispatch.mandi_tax),0)).scalar() or 0
    vikas=db.query(func.coalesce(func.sum(Dispatch.vikas_sulk),0)).scalar() or 0
    return {'total_farmers':total_farmers,'total_bookings':total_bookings,'acres':acres,'with_seed_acres':with_seed,'without_seed_acres':without_seed,'contracted_bags':contracted,'delivered_bags':delivered,'pending_bags':contracted-delivered,'seed_outstanding':seed_value-paid,'bardana_issued':bardana,'mandi_tax':mandi,'vikas_sulk':vikas}

def commitment_dict(c,db):
    delivered=db.query(func.coalesce(func.sum(DispatchLine.bags),0)).filter(DispatchLine.commitment_id==c.id).scalar() or 0
    balance=c.contracted_bags-delivered
    status='Completed' if balance==0 else ('Excess Supplied' if balance<0 else ('In Progress' if delivered>0 else 'Not Started'))
    return {'id':c.id,'month':c.contract_month,'year':c.contract_year,'variety':c.booking_variety.variety if c.booking_variety else None,'contracted_bags':c.contracted_bags,'delivered_bags':delivered,'balance_bags':balance,'status':status,'destination':c.destination,'buyback_rate':c.buyback_rate}

@app.get('/api/reports/contracts.csv')
def contracts_csv(db:Session=Depends(get_db), user:User=Depends(current_user)):
    f=io.StringIO(); w=csv.writer(f); w.writerow(['Farmer','Village','Booking','Month','Year','Variety','Contracted Bags','Delivered Bags','Balance','Destination','Status'])
    for c in db.query(Commitment).all():
        x=commitment_dict(c,db); w.writerow([c.booking.farmer.name,c.booking.farmer.village,c.booking.booking_code,x['month'],x['year'],x['variety'],x['contracted_bags'],x['delivered_bags'],x['balance_bags'],x['destination'],x['status']])
    f.seek(0); return StreamingResponse(iter([f.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=contract_status.csv'})

@app.get('/api/audit')
def audits(db:Session=Depends(get_db), user:User=Depends(current_user)):
    return [{'id':a.id,'entity':a.entity,'entity_id':a.entity_id,'action':a.action,'details':a.details,'created_at':a.created_at.isoformat()} for a in db.query(AuditLog).order_by(AuditLog.id.desc()).limit(100).all()]
