import pytest
from fastapi.testclient import TestClient
from datetime import date, datetime
import io, json, uuid
import openpyxl

from app.main import app
from app.models import Base, User, Farmer, Booking, Season
from app.database import get_db, SessionLocal
from app.auth import pw_hash

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health_endpoint(client):
    r = client.get('/health')
    assert r.status_code == 200
    data = r.json()
    assert data['status'] == 'healthy'
    assert data['version'] == '3.0.0'
    assert 'database' in data
    assert data['database']['status'] == 'ok'

def test_password_strength_validation(client):
    # Log in as admin
    login_res = client.post('/api/login', json={'email': 'admin@greenfay.local', 'password': 'admin123'})
    assert login_res.status_code == 200

    u_tag = uuid.uuid4().hex[:6]

    # Weak passwords should be rejected with 400
    weak_cases = ['short', 'nouppercase123', 'NOLOWERCASE123', 'NoDigitsHere!']
    for weak in weak_cases:
        r = client.post('/api/users', json={'name': 'Test User', 'email': f'test_{weak}_{u_tag}@greenfay.com', 'role': 'operator', 'password': weak})
        assert r.status_code == 400, f"Expected weak password '{weak}' to fail"

    # Strong password should succeed
    strong_email = f"strong_{u_tag}@greenfay.com"
    r = client.post('/api/users', json={'name': 'Strong User', 'email': strong_email, 'role': 'operator', 'password': 'StrongPassword123!'})
    assert r.status_code == 200
    assert r.json()['email'] == strong_email

def test_account_lockout_mechanism(client):
    u_tag = uuid.uuid4().hex[:6]
    test_email = f"lockout_{u_tag}@greenfay.com"

    # Create a user to test lockout
    client.post('/api/login', json={'email': 'admin@greenfay.local', 'password': 'admin123'})
    client.post('/api/users', json={'name': 'Lockout Tester', 'email': test_email, 'role': 'operator', 'password': 'ValidPassword123!'})
    client.post('/api/logout')

    # Fail 5 times (attempts 1 through 5 return 401)
    for i in range(5):
        r = client.post('/api/login', json={'email': test_email, 'password': 'WrongPassword123!'})
        assert r.status_code == 401, f"Attempt {i+1} should return 401"

    # 6th attempt must be blocked with 403 Forbidden due to lockout
    r = client.post('/api/login', json={'email': test_email, 'password': 'ValidPassword123!'})
    assert r.status_code == 403
    assert 'temporarily locked' in r.json()['detail'].lower()

def test_season_lock_enforcement(client):
    client.post('/api/login', json={'email': 'admin@greenfay.local', 'password': 'admin123'})

    s_name = f"Locked-{uuid.uuid4().hex[:6]}"
    # Create a season to lock
    s_res = client.post('/api/masters/seasons', json={'name': s_name, 'start_date': '2023-04-01', 'end_date': '2024-03-31', 'active': False})
    assert s_res.status_code == 200
    s_id = s_res.json()['id']

    # Lock season
    lock_res = client.post(f'/api/masters/seasons/{s_id}/lock', json={'reason': 'Historical audit closing'})
    assert lock_res.status_code == 200
    assert lock_res.json()['status'] == 'Locked'

    # Attempting to create a booking for this locked season should be rejected with 400
    farmer_res = client.get('/api/farmers')
    farmers = farmer_res.json().get('items', [])
    assert len(farmers) > 0
    f_id = farmers[0]['id']

    booking_res = client.post('/api/bookings', json={
        'farmer_id': f_id,
        'season': s_name,
        'season_id': s_id,
        'booking_type': 'With Seed',
        'total_acres': 5
    })
    assert booking_res.status_code == 400
    assert 'locked' in booking_res.json()['detail'].lower()

    # Unlocking requires a mandatory reason
    unlock_fail = client.post(f'/api/masters/seasons/{s_id}/unlock', json={'reason': '  '})
    assert unlock_fail.status_code == 400

    unlock_ok = client.post(f'/api/masters/seasons/{s_id}/unlock', json={'reason': 'Auditor requested access for adjustment'})
    assert unlock_ok.status_code == 200
    assert unlock_ok.json()['status'] == 'Open'

def test_document_attachments(client):
    client.post('/api/login', json={'email': 'admin@greenfay.local', 'password': 'admin123'})
    
    # Upload test document
    fake_pdf = io.BytesIO(b"%PDF-1.4 Fake PDF Content")
    fake_pdf.name = "contract_signed.pdf"
    
    upload_res = client.post(
        '/api/documents/upload',
        data={'entity_type': 'Farmer', 'entity_id': 1, 'document_type': 'Agreement', 'notes': 'Signed agreement copy'},
        files={'file': ('contract_signed.pdf', fake_pdf, 'application/pdf')}
    )
    assert upload_res.status_code == 200
    doc = upload_res.json()
    assert doc['filename'] == 'contract_signed.pdf'
    doc_id = doc['id']

    # List documents
    list_res = client.get('/api/documents/Farmer/1')
    assert list_res.status_code == 200
    docs = list_res.json()
    assert any(d['id'] == doc_id for d in docs)

    # Download document
    dl_res = client.get(f'/api/documents/{doc_id}/download')
    assert dl_res.status_code == 200
    assert dl_res.content == b"%PDF-1.4 Fake PDF Content"

    # Delete document
    del_res = client.delete(f'/api/documents/{doc_id}')
    assert del_res.status_code == 200

def test_excel_migration_staged_workflow(client):
    client.post('/api/login', json={'email': 'admin@greenfay.local', 'password': 'admin123'})

    # 1. Create in-memory sample Excel spreadsheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bookings"
    ws.append(["Farmer Name", "Father Name", "Mobile", "Village", "Acres", "Variety", "Contract Bags", "Month"])
    u_mobile1 = f"98{uuid.uuid4().int % 100000000:08d}"
    u_mobile2 = f"97{uuid.uuid4().int % 100000000:08d}"
    ws.append(["Surjit Singh", "Jagtar Singh", u_mobile1, "Mukerian", 4.0, "LR", 1000, "January"])
    ws.append(["Harpreet Kaur", "Mohan Singh", u_mobile2, "Dasuya", 2.5, "Fry Sona", 600, "February"])
    excel_buf = io.BytesIO()
    wb.save(excel_buf)
    excel_buf.seek(0)

    # 2. Upload file
    u_fname = f"historical_{uuid.uuid4().hex[:6]}.xlsx"
    up_res = client.post(
        '/api/migration/upload',
        data={'source_type': 'Booking', 'notes': 'Test Batch Upload'},
        files={'file': (u_fname, excel_buf, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    )
    assert up_res.status_code == 200
    batch_data = up_res.json()
    batch_id = batch_data['batch_id']
    assert 'Bookings' in batch_data['sheets']

    # 3. Apply column mapping
    mapping = {
        "Farmer Name": "farmer_name",
        "Father Name": "relation_name",
        "Mobile": "mobile",
        "Village": "village",
        "Acres": "acres",
        "Variety": "variety",
        "Contract Bags": "contracted_bags",
        "Month": "contract_month"
    }
    map_res = client.post(f'/api/migration/batches/{batch_id}/map', json={'sheet_name': 'Bookings', 'mapping': mapping})
    assert map_res.status_code == 200
    map_data = map_res.json()
    assert map_data['total_rows'] == 2

    # 4. Preview staged rows
    prev_res = client.get(f'/api/migration/batches/{batch_id}/preview')
    assert prev_res.status_code == 200
    items = prev_res.json()['items']
    assert len(items) == 2
    assert items[0]['data']['farmer_name'] == 'Surjit Singh'

    # 5. Execute import transactionally
    exec_res = client.post(f'/api/migration/batches/{batch_id}/execute')
    assert exec_res.status_code == 200
    rec = exec_res.json()['reconciliation']
    assert rec['imported_rows'] == 2
    assert rec['new_bookings'] == 2
    assert rec['total_acres_imported'] == 6.5
    assert rec['total_bags_imported'] == 1600.0

    # 6. Verify reconciliation report downloads
    xlsx_rec = client.get(f'/api/migration/batches/{batch_id}/reconciliation?format=xlsx')
    assert xlsx_rec.status_code == 200
    assert len(xlsx_rec.content) > 0

    pdf_rec = client.get(f'/api/migration/batches/{batch_id}/reconciliation?format=pdf')
    assert pdf_rec.status_code == 200
    assert len(pdf_rec.content) > 0

    # 7. Test rollback
    rb_res = client.post(f'/api/migration/batches/{batch_id}/rollback')
    assert rb_res.status_code == 200
    assert rb_res.json()['rolled_back_bookings'] == 2

