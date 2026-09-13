from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import openpyxl
import hashlib, os, json, uuid, re
from datetime import datetime, date

from app.database import get_db
from app.models import (
    MigrationBatch, MigrationRow, MigrationMappingTemplate,
    Farmer, Booking, BookingVariety, Commitment, SeedIssue, SeedPayment,
    BardanaIssue, Dispatch, DispatchLine, Variety, Village, Season, Destination, User
)
from app.auth import current_user, require_roles, audit, code
from app.routers.reports import make_xlsx, make_pdf

router = APIRouter()

STAGING_DIR = os.getenv('UPLOAD_DIR', os.path.join(os.getcwd(), 'uploads', 'staging'))
os.makedirs(STAGING_DIR, exist_ok=True)

DEFAULT_TEMPLATES = {
    'Booking': {
        'farmer_name': ['farmer name', 'farmer', 'name', 'kisan name'],
        'relation_name': ['father name', 'f.name', 'f/name', 'relation name', 'father/husband'],
        'mobile': ['mobile', 'phone', 'contact', 'mobile no', 'phone no'],
        'village': ['village', 'vill', 'vill.', 'pind'],
        'address': ['address', 'pata', 'location'],
        'agreement_no': ['agreement no', 'agreement', 'agr no', 'contract no'],
        'receipt_no': ['receipt no', 'receipt', 'slip no'],
        'acres': ['acres', 'acre', 'total acres', 'area'],
        'variety': ['variety', 'potato variety', 'seed variety'],
        'seed_type': ['seed type', 'type', 'program'],
        'seed_packets': ['seed packets', 'packets', 'pkt', 'seed pkt'],
        'contracted_bags': ['contracted bags', 'bags', 'contract bags', 'total bags', 'expected bags'],
        'contract_month': ['month', 'contract month', 'delivery month', 'target month'],
        'buyback_rate': ['buyback rate', 'rate', 'rate per bag', 'price'],
        'destination': ['destination', 'delivery point', 'plant/cold store', 'store'],
        'remarks': ['remarks', 'notes', 'comments']
    },
    'Without Seed': {
        'farmer_name': ['farmer', 'farmer name', 'name'],
        'village': ['village', 'vill'],
        'acres': ['acres', 'acre'],
        'variety': ['variety'],
        'contracted_bags': ['contract bags', 'bags', 'quantity'],
        'contract_month': ['month', 'delivery month'],
        'buyback_rate': ['rate', 'price'],
        'destination': ['destination', 'store'],
        'agreement_no': ['agreement', 'agreement no'],
        'remarks': ['remarks']
    },
    'Dispatch': {
        'dispatch_date': ['date', 'dispatch date', 'challan date'],
        'farmer_name': ['farmer', 'farmer name', 'grower'],
        'village': ['village', 'vill'],
        'variety': ['variety'],
        'bags': ['bags', 'quantity', 'pkt'],
        'actual_weight_kg': ['weight', 'actual weight', 'gross weight', 'weighbridge'],
        'mandi_weight_kg': ['mandi weight', 'taxable weight', 'kanda weight'],
        'truck_no': ['truck no', 'truck', 'vehicle no', 'lorry no'],
        'destination': ['destination', 'plant', 'store'],
        'gatepass_no': ['gatepass', 'gatepass no', 'gp no'],
        'nine_r_no': ['9r', '9r no', 'form 9r']
    }
}

def normalize_text(v: str) -> str:
    if not v: return ''
    v = str(v).strip()
    return ' '.join(v.split())

def normalize_title(v: str) -> str:
    v = normalize_text(v)
    return v.title() if v else ''

def normalize_mobile(v) -> str:
    if not v: return ''
    s = re.sub(r'\D', '', str(v))
    if len(s) > 10 and s.startswith('91'):
        s = s[2:]
    return s[-10:] if len(s) >= 10 else s

def normalize_float(v, default=0.0) -> float:
    if v is None: return default
    try:
        if isinstance(v, (int, float)): return float(v)
        cleaned = re.sub(r'[^\d.-]', '', str(v))
        return float(cleaned) if cleaned else default
    except Exception:
        return default

def normalize_date(v) -> str:
    if not v: return str(date.today())
    if isinstance(v, (datetime, date)):
        return v.strftime('%Y-%m-%d')
    s = str(v).strip()
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%d %b %Y'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return str(date.today())

def score_farmer_match(candidate: Farmer, name: str, relation: str, mobile: str, village: str) -> tuple[int, str]:
    score = 0
    c_name = normalize_text(candidate.name).lower()
    t_name = normalize_text(name).lower()
    
    if c_name == t_name: score += 40
    elif t_name in c_name or c_name in t_name: score += 20
    
    if mobile and candidate.mobile:
        c_mob = normalize_mobile(candidate.mobile)
        t_mob = normalize_mobile(mobile)
        if c_mob == t_mob: score += 40
        
    if village and candidate.village:
        c_vil = normalize_text(candidate.village).lower()
        t_vil = normalize_text(village).lower()
        if c_vil == t_vil: score += 15
        elif t_vil in c_vil or c_vil in t_vil: score += 8

    if relation and candidate.relation_name:
        c_rel = normalize_text(candidate.relation_name).lower()
        t_rel = normalize_text(relation).lower()
        if c_rel == t_rel: score += 15

    if score >= 80: confidence = 'Exact'
    elif score >= 55: confidence = 'Likely Match'
    elif score >= 35: confidence = 'Possible Match'
    else: confidence = 'No Match'
    return score, confidence

@router.get('/migration/templates')
def get_migration_templates(db: Session = Depends(get_db), user: User = Depends(current_user)):
    custom = db.query(MigrationMappingTemplate).all()
    out = dict(DEFAULT_TEMPLATES)
    for c in custom:
        try:
            out[c.name] = json.loads(c.mapping_json)
        except Exception:
            pass
    return out

@router.post('/migration/upload')
async def upload_migration_file(
    file: UploadFile = File(...),
    source_type: str = Form('Booking'),
    notes: str = Form(''),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles('admin', 'operator'))
):
    orig_name = file.filename or 'upload.xlsx'
    _, ext = os.path.splitext(orig_name.lower())
    if ext not in ['.xlsx', '.xlsm', '.xltx']:
        raise HTTPException(400, 'Only Excel .xlsx spreadsheets are supported')

    contents = await file.read()
    file_hash = hashlib.sha256(contents).hexdigest()

    # Check for duplicate upload
    existing = db.query(MigrationBatch).filter(MigrationBatch.file_hash == file_hash).first()
    warning = None
    if existing:
        warning = f"This exact spreadsheet was previously uploaded as batch {existing.batch_code} ({existing.status})"

    batch_uuid = str(uuid.uuid4())[:8]
    batch_code = f"MB-{datetime.now().strftime('%y%m%d')}-{batch_uuid.upper()}"
    saved_path = os.path.join(STAGING_DIR, f"{batch_code}.xlsx")
    with open(saved_path, 'wb') as f:
        f.write(contents)

    # Read sheet names and top 5 headers
    try:
        wb = openpyxl.load_workbook(saved_path, read_only=True, data_only=True)
        sheets = wb.sheetnames
        sheet_headers = {}
        for s in sheets:
            ws = wb[s]
            headers = []
            for row in ws.iter_rows(max_row=3, values_only=True):
                non_empty = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
                if len(non_empty) >= 2:
                    headers = [str(cell).strip() if cell is not None else '' for cell in row]
                    break
            sheet_headers[s] = [h for h in headers if h]
        wb.close()
    except Exception as e:
        raise HTTPException(400, f"Error inspecting Excel workbook: {str(e)}")

    batch = MigrationBatch(
        batch_code=batch_code,
        filename=orig_name,
        file_hash=file_hash,
        source_type=source_type,
        uploaded_by_id=user.id,
        status='Uploaded',
        notes=notes
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # Auto-suggestion based on templates
    template = DEFAULT_TEMPLATES.get(source_type, {})
    suggested_mapping = {}
    primary_sheet = sheets[0] if sheets else ''
    headers_for_primary = sheet_headers.get(primary_sheet, [])
    for col in headers_for_primary:
        c_lower = col.lower().strip()
        matched_field = None
        for field, aliases in template.items():
            if c_lower in aliases:
                matched_field = field
                break
        if matched_field:
            suggested_mapping[col] = matched_field

    audit(db, user, 'MigrationBatch', batch.id, 'UPLOAD', f"Uploaded {orig_name} ({len(sheets)} sheets)", module='Migration')
    db.commit()

    return {
        'batch_id': batch.id,
        'batch_code': batch.batch_code,
        'filename': batch.filename,
        'sheets': sheets,
        'sheet_headers': sheet_headers,
        'suggested_mapping': suggested_mapping,
        'warning': warning
    }

@router.post('/migration/batches/{id}/map')
async def apply_batch_mapping(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles('admin', 'operator'))
):
    d = await request.json()
    batch = db.get(MigrationBatch, id)
    if not batch:
        raise HTTPException(404, 'Batch not found')

    sheet_name = d.get('sheet_name')
    mapping = d.get('mapping', {})  # { "EXCEL_COL": "platform_field" }
    save_as_template = d.get('save_template_name')

    if save_as_template:
        tmpl = db.query(MigrationMappingTemplate).filter(MigrationMappingTemplate.name == save_as_template).first()
        if not tmpl:
            tmpl = MigrationMappingTemplate(name=save_as_template, source_type=batch.source_type, mapping_json=json.dumps(mapping))
            db.add(tmpl)
        else:
            tmpl.mapping_json = json.dumps(mapping)

    batch.mapping_config_json = json.dumps({'sheet': sheet_name, 'mapping': mapping})
    batch.status = 'Validating'
    db.commit()

    # Clear prior staging rows for this batch if re-mapping
    db.query(MigrationRow).filter(MigrationRow.batch_id == batch.id).delete()
    db.commit()

    file_path = os.path.join(STAGING_DIR, f"{batch.batch_code}.xlsx")
    if not os.path.exists(file_path):
        raise HTTPException(404, 'Staged workbook file missing')

    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb[sheet_name] if sheet_name and sheet_name in wb.sheetnames else wb.active

    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        raise HTTPException(400, 'Selected sheet has no rows')

    # Find header row
    header_idx = -1
    for idx, row in enumerate(rows[:5]):
        str_cells = [str(c).strip() for c in row if c is not None]
        if any(c in mapping for c in str_cells):
            header_idx = idx
            break
    if header_idx == -1:
        header_idx = 0

    headers = [str(c).strip() if c is not None else f"Col_{i}" for i, c in enumerate(rows[header_idx])]
    data_rows = rows[header_idx + 1:]

    # Preload existing farmers for fuzzy matching
    existing_farmers = db.query(Farmer).filter(Farmer.active == True).all()

    total = 0
    valid_count = 0
    warning_count = 0
    error_count = 0

    staged_objects = []

    for r_idx, row_vals in enumerate(data_rows, start=header_idx + 2):
        if not any(row_vals):
            continue  # skip completely blank rows

        raw_dict = {}
        for ci, val in enumerate(row_vals):
            if ci < len(headers):
                raw_dict[headers[ci]] = val

        # Normalize mapped fields
        norm_dict = {}
        for src_col, target_field in mapping.items():
            if target_field and target_field != 'ignore' and src_col in raw_dict:
                norm_dict[target_field] = raw_dict[src_col]

        # Field-specific normalization
        farmer_name = normalize_title(norm_dict.get('farmer_name', ''))
        relation_name = normalize_title(norm_dict.get('relation_name', ''))
        village = normalize_title(norm_dict.get('village', ''))
        mobile = normalize_mobile(norm_dict.get('mobile', ''))
        variety = normalize_text(norm_dict.get('variety', 'LR'))
        acres = normalize_float(norm_dict.get('acres', 0))
        bags = normalize_float(norm_dict.get('contracted_bags', 0))
        seed_packets = normalize_float(norm_dict.get('seed_packets', 0))
        buyback_rate = normalize_float(norm_dict.get('buyback_rate', 0))
        contract_month = normalize_title(norm_dict.get('contract_month', 'January'))
        agreement_no = normalize_text(norm_dict.get('agreement_no', ''))

        norm_dict.update({
            'farmer_name': farmer_name,
            'relation_name': relation_name,
            'village': village,
            'mobile': mobile,
            'variety': variety,
            'acres': acres,
            'contracted_bags': bags,
            'seed_packets': seed_packets,
            'buyback_rate': buyback_rate,
            'contract_month': contract_month,
            'agreement_no': agreement_no
        })

        warnings = []
        errors = []

        if not farmer_name:
            errors.append('Missing mandatory Farmer Name')
        if acres < 0:
            errors.append('Acreage cannot be negative')
        if bags < 0:
            errors.append('Contracted bags cannot be negative')

        if not mobile:
            warnings.append('Farmer mobile number is missing')
        elif len(mobile) != 10:
            warnings.append(f"Mobile '{mobile}' is not 10 digits")

        if not village:
            warnings.append('Village is unspecified')

        # Match farmer against database
        best_farmer_id = None
        best_conf = 'No Match'
        best_score = 0

        for f in existing_farmers:
            score, conf = score_farmer_match(f, farmer_name, relation_name, mobile, village)
            if score > best_score:
                best_score = score
                best_conf = conf
                best_farmer_id = f.id

        if best_conf in ['Exact', 'Likely Match']:
            warnings.append(f"Matched existing farmer #{best_farmer_id} ({best_conf})")

        row_status = 'Error' if errors else ('Warning' if warnings else 'Valid')
        if row_status == 'Valid': valid_count += 1
        elif row_status == 'Warning': warning_count += 1
        else: error_count += 1
        total += 1

        staged_objects.append(MigrationRow(
            batch_id=batch.id,
            sheet_name=sheet_name,
            row_number=r_idx,
            raw_data_json=json.dumps(raw_dict, default=str),
            normalized_data_json=json.dumps(norm_dict, default=str),
            status=row_status,
            warning_messages_json=json.dumps(warnings) if warnings else None,
            error_messages_json=json.dumps(errors) if errors else None,
            match_farmer_id=best_farmer_id if best_score >= 35 else None,
            match_confidence=best_conf,
            match_decision='Link' if best_score >= 55 else 'Create'
        ))

    db.add_all(staged_objects)
    batch.total_rows = total
    batch.valid_rows = valid_count
    batch.warning_rows = warning_count
    batch.rejected_rows = error_count
    batch.status = 'Review Required' if (warning_count > 0 or error_count > 0) else 'Ready'
    audit(db, user, 'MigrationBatch', batch.id, 'MAP', f"Parsed {total} rows: {valid_count} valid, {warning_count} warnings, {error_count} errors", module='Migration')
    db.commit()

    return {
        'total_rows': total,
        'valid_rows': valid_count,
        'warning_rows': warning_count,
        'error_rows': error_count,
        'status': batch.status
    }

@router.get('/migration/batches/{id}/preview')
def get_batch_preview(
    id: int,
    status_filter: str = '',
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    batch = db.get(MigrationBatch, id)
    if not batch:
        raise HTTPException(404, 'Batch not found')

    q = db.query(MigrationRow).filter(MigrationRow.batch_id == batch.id)
    if status_filter:
        q = q.filter(MigrationRow.status == status_filter)

    total_filtered = q.count()
    rows = q.order_by(MigrationRow.row_number.asc()).offset((page - 1) * per_page).limit(per_page).all()

    items = []
    for r in rows:
        norm = json.loads(r.normalized_data_json) if r.normalized_data_json else {}
        matched_farmer_name = None
        if r.match_farmer_id:
            mf = db.get(Farmer, r.match_farmer_id)
            if mf: matched_farmer_name = f"{mf.name} ({mf.village or ''})"

        items.append({
            'id': r.id,
            'row_number': r.row_number,
            'status': r.status,
            'data': norm,
            'warnings': json.loads(r.warning_messages_json) if r.warning_messages_json else [],
            'errors': json.loads(r.error_messages_json) if r.error_messages_json else [],
            'match_farmer_id': r.match_farmer_id,
            'match_farmer_name': matched_farmer_name,
            'match_confidence': r.match_confidence,
            'match_decision': r.match_decision
        })

    return {
        'batch': {
            'id': batch.id,
            'batch_code': batch.batch_code,
            'filename': batch.filename,
            'source_type': batch.source_type,
            'status': batch.status,
            'total_rows': batch.total_rows,
            'valid_rows': batch.valid_rows,
            'warning_rows': batch.warning_rows,
            'rejected_rows': batch.rejected_rows,
            'imported_rows': batch.imported_rows
        },
        'items': items,
        'total': total_filtered,
        'page': page,
        'per_page': per_page
    }

@router.post('/migration/batches/{id}/resolve-farmer')
async def resolve_batch_farmer(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles('admin', 'operator'))
):
    d = await request.json()
    row_id = d.get('row_id')
    decision = d.get('decision')  # Link, Create, Ignore
    farmer_id = d.get('farmer_id')

    if row_id:
        row = db.get(MigrationRow, row_id)
        if not row or row.batch_id != id:
            raise HTTPException(404, 'Row not found')
        row.match_decision = decision
        if farmer_id:
            row.match_farmer_id = farmer_id
    else:
        # Bulk decision for all matched rows in batch
        db.query(MigrationRow).filter(
            MigrationRow.batch_id == id,
            MigrationRow.match_confidence.in_(['Exact', 'Likely Match'])
        ).update({'match_decision': decision})

    db.commit()
    return {'ok': True}

@router.post('/migration/batches/{id}/execute')
def execute_batch_import(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles('admin', 'operator'))
):
    batch = db.get(MigrationBatch, id)
    if not batch:
        raise HTTPException(404, 'Batch not found')
    if batch.status in ['Completed', 'Importing']:
        raise HTTPException(400, f"Batch is already {batch.status}")

    batch.status = 'Importing'
    db.commit()

    rows = db.query(MigrationRow).filter(
        MigrationRow.batch_id == batch.id,
        MigrationRow.status != 'Error',
        MigrationRow.match_decision != 'Ignore'
    ).order_by(MigrationRow.row_number.asc()).all()

    # Active season
    active_season = db.query(Season).filter(Season.active == True).first()
    season_name = active_season.name if active_season else '2025-26'
    season_id = active_season.id if active_season else None

    imported_count = 0
    new_farmers_count = 0
    matched_farmers_count = 0
    new_bookings_count = 0
    total_acres_imported = 0.0
    total_bags_imported = 0.0

    try:
        for r in rows:
            norm = json.loads(r.normalized_data_json) if r.normalized_data_json else {}
            farmer_name = norm.get('farmer_name')
            if not farmer_name:
                continue

            # Farmer resolution
            target_farmer = None
            if r.match_decision == 'Link' and r.match_farmer_id:
                target_farmer = db.get(Farmer, r.match_farmer_id)
                if target_farmer:
                    matched_farmers_count += 1

            if not target_farmer:
                target_farmer = Farmer(
                    name=farmer_name,
                    relation_name=norm.get('relation_name'),
                    mobile=norm.get('mobile'),
                    village=norm.get('village'),
                    address=norm.get('address'),
                    district=norm.get('district', 'Hoshiarpur'),
                    state=norm.get('state', 'Punjab'),
                    active=True
                )
                db.add(target_farmer)
                db.flush()
                target_farmer.farmer_code = code('FAR', target_farmer.id)
                new_farmers_count += 1

            # Booking creation
            acres = float(norm.get('acres') or 1.0)
            bags = float(norm.get('contracted_bags') or 0.0)
            variety_name = norm.get('variety') or 'LR'
            seed_type = norm.get('seed_type') or ('With Seed' if norm.get('seed_packets', 0) > 0 else 'Without Seed')

            booking = Booking(
                farmer_id=target_farmer.id,
                season=season_name,
                season_id=season_id,
                booking_date=date.today(),
                agreement_no=norm.get('agreement_no'),
                receipt_no=norm.get('receipt_no'),
                booking_type=seed_type,
                total_acres=acres,
                destination=norm.get('destination', 'Main Cold Store'),
                status='Active',
                remarks=f"Imported from {batch.batch_code} row #{r.row_number}",
                created_by_id=user.id
            )
            db.add(booking)
            db.flush()
            booking.booking_code = code('BKG', booking.id)
            new_bookings_count += 1
            total_acres_imported += acres

            # Variety line
            bv = BookingVariety(
                booking_id=booking.id,
                variety=variety_name,
                acres=acres,
                seed_type=seed_type,
                planned_seed_packets=float(norm.get('seed_packets') or 0),
                expected_buyback_qty=bags
            )
            db.add(bv)
            db.flush()

            # Month-wise commitment
            if bags > 0:
                c = Commitment(
                    booking_id=booking.id,
                    booking_variety_id=bv.id,
                    contract_month=norm.get('contract_month', 'January'),
                    contract_year=date.today().year + (1 if date.today().month >= 4 else 0),
                    contracted_bags=bags,
                    buyback_rate=float(norm.get('buyback_rate') or 0),
                    destination=booking.destination,
                    status='Not Started'
                )
                db.add(c)
                total_bags_imported += bags

            r.status = 'Imported'
            r.final_entity_type = 'Booking'
            r.final_entity_id = booking.id
            imported_count += 1

        reconciliation = {
            'total_source_rows': batch.total_rows,
            'imported_rows': imported_count,
            'new_farmers': new_farmers_count,
            'matched_farmers': matched_farmers_count,
            'new_bookings': new_bookings_count,
            'total_acres_imported': round(total_acres_imported, 2),
            'total_bags_imported': round(total_bags_imported, 2),
            'completed_at': str(datetime.now())
        }

        batch.imported_rows = imported_count
        batch.status = 'Completed'
        batch.completed_at = datetime.utcnow()
        batch.reconciliation_json = json.dumps(reconciliation)

        audit(db, user, 'MigrationBatch', batch.id, 'IMPORT', f"Executed batch: {imported_count} rows imported", module='Migration')
        db.commit()

        return {'ok': True, 'reconciliation': reconciliation}

    except Exception as e:
        db.rollback()
        batch.status = 'Failed'
        batch.notes = f"Execution error: {str(e)}"
        db.commit()
        raise HTTPException(500, f"Transactional import failed: {str(e)}")

@router.get('/migration/batches/{id}/reconciliation')
def get_batch_reconciliation(
    id: int,
    format: str = '',
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    batch = db.get(MigrationBatch, id)
    if not batch:
        raise HTTPException(404, 'Batch not found')

    rec = json.loads(batch.reconciliation_json) if batch.reconciliation_json else {}

    if format == 'xlsx':
        headers = ['Metric', 'Value']
        rows = [
            ['Batch Code', batch.batch_code],
            ['Source Spreadsheet', batch.filename],
            ['Source Type', batch.source_type],
            ['Execution Status', batch.status],
            ['Total Source Rows', batch.total_rows],
            ['Imported Rows', rec.get('imported_rows', batch.imported_rows)],
            ['New Farmers Created', rec.get('new_farmers', 0)],
            ['Existing Farmers Linked', rec.get('matched_farmers', 0)],
            ['Bookings Created', rec.get('new_bookings', 0)],
            ['Total Acres Imported', rec.get('total_acres_imported', 0)],
            ['Total Bags Imported', rec.get('total_bags_imported', 0)],
            ['Completed At', rec.get('completed_at', '')]
        ]
        buf = make_xlsx(f"Reconciliation - {batch.batch_code}", headers, rows)
        return StreamingResponse(buf, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f"attachment; filename=reconciliation_{batch.batch_code}.xlsx"})

    elif format == 'pdf':
        headers = ['Reconciliation Metric', 'Details']
        rows = [
            ['Batch Code', batch.batch_code],
            ['Filename', batch.filename],
            ['Status', batch.status],
            ['Total Source Rows', str(batch.total_rows)],
            ['Imported Rows', str(rec.get('imported_rows', batch.imported_rows))],
            ['New Farmers', str(rec.get('new_farmers', 0))],
            ['Matched Farmers', str(rec.get('matched_farmers', 0))],
            ['Total Acres', str(rec.get('total_acres_imported', 0))],
            ['Total Bags', str(rec.get('total_bags_imported', 0))]
        ]
        buf = make_pdf(f"Migration Reconciliation: {batch.batch_code}", headers, rows)
        return StreamingResponse(buf, media_type='application/pdf', headers={'Content-Disposition': f"attachment; filename=reconciliation_{batch.batch_code}.pdf"})

    return {'batch_code': batch.batch_code, 'status': batch.status, 'reconciliation': rec}

@router.post('/migration/batches/{id}/rollback')
def rollback_batch(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles('admin'))
):
    batch = db.get(MigrationBatch, id)
    if not batch:
        raise HTTPException(404, 'Batch not found')
    if batch.status != 'Completed':
        raise HTTPException(400, 'Only completed batches can be rolled back')

    # Find created bookings
    rows = db.query(MigrationRow).filter(
        MigrationRow.batch_id == batch.id,
        MigrationRow.final_entity_type == 'Booking',
        MigrationRow.final_entity_id != None
    ).all()

    booking_ids = [r.final_entity_id for r in rows if r.final_entity_id]

    # Verify no finalized dispatches exist against these bookings
    active_dispatches = db.query(DispatchLine).join(Dispatch).filter(
        DispatchLine.booking_id.in_(booking_ids),
        Dispatch.status == 'Finalized'
    ).first()

    if active_dispatches:
        raise HTTPException(400, 'Cannot rollback: Dependent finalized dispatches have already been posted against imported bookings.')

    # Delete commitments, varieties, and bookings
    db.query(Commitment).filter(Commitment.booking_id.in_(booking_ids)).delete(synchronize_session=False)
    db.query(BookingVariety).filter(BookingVariety.booking_id.in_(booking_ids)).delete(synchronize_session=False)
    db.query(Booking).filter(Booking.id.in_(booking_ids)).delete(synchronize_session=False)

    for r in rows:
        r.status = 'Ignored'
        r.final_entity_id = None

    batch.status = 'Rolled Back'
    audit(db, user, 'MigrationBatch', batch.id, 'ROLLBACK', f"Rolled back {len(booking_ids)} imported bookings", module='Migration')
    db.commit()

    return {'ok': True, 'rolled_back_bookings': len(booking_ids)}

