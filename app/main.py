from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import date, datetime, timedelta, timezone
import os, json, csv, io, uuid, logging

from .database import init_db, get_db, SessionLocal, check_db_connectivity
from .models import (
    User, Farmer, Booking, BookingVariety, Commitment, SeedIssue, SeedPayment,
    BardanaIssue, Dispatch, DispatchLine, AuditLog, TaxRate, Season, Variety,
    Destination, Supplier, BardanaType, Village
)
from .routers import masters, farmers, bookings, seed, bardana, dispatch, reports, users, documents, migration
from .auth import pw_hash, pw_verify, sign_token, parse_token, current_user, audit, code

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('greenfay')

def seed_data():
    db = SessionLocal()
    try:
        app_env = os.getenv('APP_ENV', 'development')
        if db.query(User).count() == 0:
            initial_pw = os.getenv('INITIAL_ADMIN_PASSWORD', 'admin123')
            db.add(User(email='admin@greenfay.local', name='GreenFay Admin', role='admin', password_hash=pw_hash(initial_pw)))
            db.commit()

        if db.query(TaxRate).count() == 0:
            db.add_all([
                TaxRate(effective_from=date(2025,1,1), effective_to=date(2025,6,30), mandi_rate_per_qtl=6, vikas_rate_per_qtl=3, mandi_cap=2400, vikas_cap=1200),
                TaxRate(effective_from=date(2025,7,1), effective_to=None, mandi_rate_per_qtl=5, vikas_rate_per_qtl=2.5, mandi_cap=2000, vikas_cap=1000),
            ])
            db.commit()
        
        # Master data
        if db.query(Season).count() == 0:
            db.add(Season(name='2025-26', start_date=date(2025,4,1), end_date=date(2026,3,31), active=True, status='Open'))
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
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_data()
    yield

app = FastAPI(
    title='Green Fay Contract Farming Platform',
    version='3.0.0',
    lifespan=lifespan
)

app.mount('/static', StaticFiles(directory='app/static'), name='static')
templates = Jinja2Templates(directory='app/templates')

# Security Headers & Cache-Control Middleware
@app.middleware('http')
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

# Global Exception Handler with Reference ID
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})
    err_ref = f"ERR-{uuid.uuid4().hex[:6].upper()}"
    logger.exception(f"Unhandled error [{err_ref}] on {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            'detail': 'An unexpected server error occurred. Please report this error reference to technical support.',
            'error_reference_id': err_ref
        }
    )

# Include routers
app.include_router(masters.router, prefix='/api/masters', tags=['masters'])
app.include_router(farmers.router, prefix='/api', tags=['farmers'])
app.include_router(bookings.router, prefix='/api', tags=['bookings'])
app.include_router(seed.router, prefix='/api/seed', tags=['seed'])
app.include_router(bardana.router, prefix='/api', tags=['bardana'])
app.include_router(dispatch.router, prefix='/api', tags=['dispatch'])
app.include_router(reports.router, prefix='/api/reports', tags=['reports'])
app.include_router(users.router, prefix='/api', tags=['users'])
app.include_router(documents.router, prefix='/api', tags=['documents'])
app.include_router(migration.router, prefix='/api', tags=['migration'])

@app.get('/health')
def health_check():
    db_health = check_db_connectivity()
    return {
        'status': 'healthy' if db_health['status'] == 'ok' else 'degraded',
        'version': '3.0.0',
        'app_env': os.getenv('APP_ENV', 'development'),
        'database': db_health
    }

@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    return FileResponse('app/templates/index.html', media_type='text/html')

@app.post('/api/login')
async def login(request: Request, response: Response, db: Session = Depends(get_db)):
    data = await request.json()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')

    u = db.query(User).filter(User.email == email).first()
    if not u or not u.active:
        raise HTTPException(401, 'Invalid email or password')

    # Account Lockout check
    if u.locked_until:
        if u.locked_until > datetime.utcnow():
            remain = int((u.locked_until - datetime.utcnow()).total_seconds() / 60) + 1
            raise HTTPException(403, f"Account is temporarily locked due to multiple failed login attempts. Try again in {remain} minutes.")
        else:
            u.locked_until = None
            u.failed_login_attempts = 0

    if not pw_verify(password, u.password_hash):
        u.failed_login_attempts = (u.failed_login_attempts or 0) + 1
        if u.failed_login_attempts >= 5:
            u.locked_until = datetime.utcnow() + timedelta(minutes=15)
        db.commit()
        raise HTTPException(401, 'Invalid email or password')

    # Login succeeded
    u.failed_login_attempts = 0
    u.locked_until = None
    u.last_login_at = datetime.utcnow()
    db.commit()

    is_prod = os.getenv('APP_ENV') == 'production'
    res = JSONResponse({
        'ok': True,
        'user': {
            'id': u.id,
            'name': u.name,
            'email': u.email,
            'role': u.role,
            'must_change_password': bool(u.must_change_password)
        }
    })
    res.set_cookie(
        'gf_session',
        sign_token(u.id),
        httponly=True,
        samesite='lax',
        secure=is_prod,
        max_age=604800
    )
    return res

@app.post('/api/logout')
def logout():
    r = JSONResponse({'ok': True})
    r.delete_cookie('gf_session')
    return r

@app.get('/api/me')
def me(user: User = Depends(current_user)):
    return {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'role': user.role,
        'must_change_password': bool(user.must_change_password)
    }

@app.get('/api/dashboard')
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    total_farmers = db.query(Farmer).filter(Farmer.active == True).count()
    total_bookings = db.query(Booking).filter(Booking.status != 'Cancelled').count()
    acres = db.query(func.coalesce(func.sum(Booking.total_acres), 0)).filter(Booking.status != 'Cancelled').scalar() or 0
    with_seed = db.query(func.coalesce(func.sum(BookingVariety.acres), 0)).join(Booking).filter(Booking.status != 'Cancelled', BookingVariety.seed_type == 'With Seed').scalar() or 0
    without_seed = db.query(func.coalesce(func.sum(BookingVariety.acres), 0)).join(Booking).filter(Booking.status != 'Cancelled', BookingVariety.seed_type == 'Without Seed').scalar() or 0
    contracted = db.query(func.coalesce(func.sum(Commitment.contracted_bags), 0)).join(Booking).filter(Booking.status != 'Cancelled').scalar() or 0
    
    # Delivered bags from finalized dispatches only
    delivered = db.query(func.coalesce(func.sum(DispatchLine.bags), 0)).join(Dispatch).filter(Dispatch.status == 'Finalized', DispatchLine.status == 'Active').scalar() or 0
    
    seed_value = db.query(func.coalesce(func.sum(SeedIssue.total_value), 0)).filter(SeedIssue.status == 'Active').scalar() or 0
    paid = db.query(func.coalesce(func.sum(SeedPayment.amount), 0)).filter(SeedPayment.status == 'Active').scalar() or 0
    bardana = db.query(func.coalesce(func.sum(BardanaIssue.bags_issued), 0)).filter(BardanaIssue.status == 'Active').scalar() or 0
    mandi = db.query(func.coalesce(func.sum(Dispatch.mandi_tax), 0)).filter(Dispatch.status == 'Finalized').scalar() or 0
    vikas = db.query(func.coalesce(func.sum(Dispatch.vikas_sulk), 0)).filter(Dispatch.status == 'Finalized').scalar() or 0

    # Operational Alert Counts
    today = date.today()
    current_month = today.strftime('%B')
    due_this_month = db.query(Commitment).join(Booking).filter(
        Booking.status != 'Cancelled',
        Commitment.contract_month == current_month,
        Commitment.status != 'Completed'
    ).count()

    draft_dispatches = db.query(Dispatch).filter(Dispatch.status == 'Draft').count()
    active_season = db.query(Season).filter(Season.active == True).first()

    return {
        'total_farmers': total_farmers,
        'total_bookings': total_bookings,
        'acres': round(acres, 2),
        'with_seed_acres': round(with_seed, 2),
        'without_seed_acres': round(without_seed, 2),
        'contracted_bags': round(contracted, 2),
        'delivered_bags': round(delivered, 2),
        'pending_bags': round(max(0, contracted - delivered), 2),
        'seed_outstanding': round(max(0, seed_value - paid), 2),
        'bardana_issued': round(bardana, 2),
        'mandi_tax': round(mandi, 2),
        'vikas_sulk': round(vikas, 2),
        'active_season': {
            'name': active_season.name if active_season else 'None',
            'status': active_season.status if active_season else 'Open'
        },
        'alerts': {
            'due_this_month': due_this_month,
            'draft_dispatches': draft_dispatches,
            'seed_outstanding_farmers': db.query(SeedIssue.farmer_id).filter(SeedIssue.status == 'Active').distinct().count()
        }
    }

def commitment_dict(c, db):
    delivered = db.query(func.coalesce(func.sum(DispatchLine.bags), 0)).join(Dispatch).filter(
        DispatchLine.commitment_id == c.id,
        Dispatch.status == 'Finalized',
        DispatchLine.status == 'Active'
    ).scalar() or 0
    balance = c.contracted_bags - delivered
    status = 'Completed' if balance == 0 else ('Excess Supplied' if balance < 0 else ('In Progress' if delivered > 0 else 'Not Started'))
    return {
        'id': c.id,
        'month': c.contract_month,
        'year': c.contract_year,
        'variety': c.booking_variety.variety if c.booking_variety else None,
        'contracted_bags': c.contracted_bags,
        'delivered_bags': delivered,
        'balance_bags': balance,
        'status': status,
        'destination': c.destination,
        'buyback_rate': c.buyback_rate
    }

@app.get('/api/reports/contracts.csv')
def contracts_csv(db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = io.StringIO()
    w = csv.writer(f)
    w.writerow(['Farmer', 'Village', 'Booking', 'Month', 'Year', 'Variety', 'Contracted Bags', 'Delivered Bags', 'Balance', 'Destination', 'Status'])
    for c in db.query(Commitment).all():
        x = commitment_dict(c, db)
        w.writerow([
            c.booking.farmer.name if c.booking and c.booking.farmer else '',
            c.booking.farmer.village if c.booking and c.booking.farmer else '',
            c.booking.booking_code if c.booking else '',
            x['month'], x['year'], x['variety'], x['contracted_bags'],
            x['delivered_bags'], x['balance_bags'], x['destination'], x['status']
        ])
    f.seek(0)
    return StreamingResponse(iter([f.getvalue()]), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename=contract_status.csv'})

@app.get('/api/audit')
def audits(db: Session = Depends(get_db), user: User = Depends(current_user)):
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(100).all()
    return [
        {
            'id': a.id,
            'entity': a.entity,
            'entity_id': a.entity_id,
            'action': a.action,
            'details': a.details,
            'module': a.module,
            'user_name': a.user_name,
            'created_at': a.created_at.isoformat() if a.created_at else ''
        }
        for a in logs
    ]
