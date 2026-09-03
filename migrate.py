import os, shutil
from sqlalchemy import create_engine, text
from app.models import Base
from app.database import DATABASE_URL as SQLALCHEMY_DATABASE_URL

def backup_db():
    db_path = 'greenfay.db'
    if os.path.exists(db_path):
        shutil.copy2(db_path, 'greenfay_pre_migrate_backup.db')
        print("Database backed up to greenfay_pre_migrate_backup.db")
    else:
        print("No existing greenfay.db found. Skipping backup.")

def add_column_safe(conn, table, col_def):
    try:
        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col_def}'))
        print(f'  Added: {table}.{col_def.split()[0]}')
    except Exception as e:
        if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower() or 'operationalerror' in str(e).lower():
            print(f'  Skip (exists or error): {table}.{col_def.split()[0]}')
        else:
            raise

def run_migration():
    backup_db()
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    # 2. Get record counts (if tables exist)
    tables_to_check = ['seed_issues', 'seed_payments', 'bardana_issues', 'dispatches', 'dispatch_lines', 'bookings', 'farmers', 'commitments', 'booking_varieties', 'audit_logs', 'tax_rates']
    counts_before = {}
    with engine.connect() as conn:
        for t in tables_to_check:
            try:
                counts_before[t] = conn.execute(text(f'SELECT COUNT(*) FROM {t}')).scalar()
            except:
                counts_before[t] = 0
    print("Record counts before migration:", counts_before)

    # 3. Create all tables/columns via SQLAlchemy (creates new tables)
    Base.metadata.create_all(bind=engine)
    
    # 4. Add columns using raw SQL for SQLite
    with engine.begin() as conn:
        # SeedIssue
        add_column_safe(conn, 'seed_issues', 'booking_variety_id INTEGER')
        add_column_safe(conn, 'seed_issues', 'supplier_id INTEGER')
        add_column_safe(conn, 'seed_issues', 'vehicle_no VARCHAR(50)')
        add_column_safe(conn, 'seed_issues', 'created_by_id INTEGER')
        add_column_safe(conn, 'seed_issues', "status VARCHAR(30) DEFAULT 'Active'")
        add_column_safe(conn, 'seed_issues', 'cancelled_by_id INTEGER')
        add_column_safe(conn, 'seed_issues', 'cancelled_at DATETIME')
        add_column_safe(conn, 'seed_issues', 'cancellation_reason TEXT')
        
        # SeedPayment
        add_column_safe(conn, 'seed_payments', 'booking_id INTEGER')
        add_column_safe(conn, 'seed_payments', 'farmer_id INTEGER')
        add_column_safe(conn, 'seed_payments', 'created_by_id INTEGER')
        add_column_safe(conn, 'seed_payments', "status VARCHAR(30) DEFAULT 'Active'")
        add_column_safe(conn, 'seed_payments', 'cancelled_by_id INTEGER')
        add_column_safe(conn, 'seed_payments', 'cancelled_at DATETIME')
        add_column_safe(conn, 'seed_payments', 'cancellation_reason TEXT')

        # BardanaIssue
        add_column_safe(conn, 'bardana_issues', 'booking_variety_id INTEGER')
        add_column_safe(conn, 'bardana_issues', 'bardana_type_id INTEGER')
        add_column_safe(conn, 'bardana_issues', 'created_by_id INTEGER')
        add_column_safe(conn, 'bardana_issues', "status VARCHAR(30) DEFAULT 'Active'")
        add_column_safe(conn, 'bardana_issues', 'cancelled_by_id INTEGER')
        add_column_safe(conn, 'bardana_issues', 'cancelled_at DATETIME')
        add_column_safe(conn, 'bardana_issues', 'cancellation_reason TEXT')

        # Dispatch
        add_column_safe(conn, 'dispatches', 'transporter_id INTEGER')
        add_column_safe(conn, 'dispatches', 'destination_id INTEGER')
        add_column_safe(conn, 'dispatches', 'tax_rate_id INTEGER')
        add_column_safe(conn, 'dispatches', 'created_by_id INTEGER')
        add_column_safe(conn, 'dispatches', "status VARCHAR(30) DEFAULT 'Draft'")
        add_column_safe(conn, 'dispatches', 'cancelled_by_id INTEGER')
        add_column_safe(conn, 'dispatches', 'cancelled_at DATETIME')
        add_column_safe(conn, 'dispatches', 'cancellation_reason TEXT')

        # DispatchLine
        add_column_safe(conn, 'dispatch_lines', 'variety_id INTEGER')
        add_column_safe(conn, 'dispatch_lines', "status VARCHAR(30) DEFAULT 'Active'")

        # Booking
        add_column_safe(conn, 'bookings', 'season_id INTEGER')
        add_column_safe(conn, 'bookings', 'destination_id INTEGER')
        add_column_safe(conn, 'bookings', 'created_by_id INTEGER')
        add_column_safe(conn, 'bookings', 'updated_by_id INTEGER')
        add_column_safe(conn, 'bookings', 'updated_at DATETIME')

        # Farmer
        add_column_safe(conn, 'farmers', 'village_id INTEGER')

        # Commitment
        add_column_safe(conn, 'commitments', 'destination_id INTEGER')
        add_column_safe(conn, 'commitments', 'default_rate FLOAT DEFAULT 0')
        add_column_safe(conn, 'commitments', 'rate_overridden BOOLEAN DEFAULT 0')
        add_column_safe(conn, 'commitments', 'override_reason TEXT')
        add_column_safe(conn, 'commitments', 'overridden_by_id INTEGER')
        # status already exists in commitments

        # BookingVariety
        add_column_safe(conn, 'booking_varieties', 'variety_id INTEGER')
        add_column_safe(conn, 'booking_varieties', 'supplier_id INTEGER')

        # AuditLog
        add_column_safe(conn, 'audit_logs', 'module VARCHAR(80)')
        add_column_safe(conn, 'audit_logs', 'old_values TEXT')
        add_column_safe(conn, 'audit_logs', 'new_values TEXT')
        add_column_safe(conn, 'audit_logs', 'user_name VARCHAR(120)')

        # TaxRate
        add_column_safe(conn, 'tax_rates', 'remarks TEXT')
        
    counts_after = {}
    with engine.connect() as conn:
        for t in tables_to_check:
            try:
                counts_after[t] = conn.execute(text(f'SELECT COUNT(*) FROM {t}')).scalar()
            except:
                counts_after[t] = 0
    
    print("Record counts after migration:", counts_after)
    if counts_before == counts_after:
        print("Migration successful: Record counts match.")
    else:
        print("Migration warning: Record counts differ!")

if __name__ == '__main__':
    run_migration()
