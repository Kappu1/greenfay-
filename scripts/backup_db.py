#!/usr/bin/env python3
import os, sys, shutil, subprocess
from datetime import datetime

# Load environment
BACKUP_DIR = os.getenv('BACKUP_DIR', os.path.join(os.getcwd(), 'backups'))
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./greenfay.db')
RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '14'))

os.makedirs(BACKUP_DIR, exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

def backup_sqlite(db_file: str):
    if not os.path.exists(db_file):
        print(f"Error: Database file '{db_file}' not found.")
        sys.exit(1)
    dest = os.path.join(BACKUP_DIR, f"greenfay_backup_{timestamp}.db")
    shutil.copy2(db_file, dest)
    size_mb = round(os.path.getsize(dest) / (1024 * 1024), 2)
    print(f"[SUCCESS] SQLite backup created: {dest} ({size_mb} MB)")
    return dest

def backup_postgres(url: str):
    dest = os.path.join(BACKUP_DIR, f"greenfay_pg_backup_{timestamp}.sql")
    # Parse URL
    # format: postgresql://user:pass@host:port/dbname
    cmd = ['pg_dump', '--dbname', url, '-f', dest, '-F', 'p', '--no-owner', '--no-privileges']
    try:
        subprocess.run(cmd, check=True)
        size_mb = round(os.path.getsize(dest) / (1024 * 1024), 2)
        print(f"[SUCCESS] PostgreSQL dump created: {dest} ({size_mb} MB)")
        return dest
    except Exception as e:
        print(f"[ERROR] pg_dump failed: {str(e)}")
        sys.exit(1)

def cleanup_old_backups():
    now = datetime.now()
    count = 0
    for fname in os.listdir(BACKUP_DIR):
        fpath = os.path.join(BACKUP_DIR, fname)
        if os.path.isfile(fpath) and fname.startswith('greenfay_'):
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if (now - mtime).days > RETENTION_DAYS:
                os.remove(fpath)
                count += 1
    if count > 0:
        print(f"[CLEANUP] Pruned {count} backup(s) older than {RETENTION_DAYS} days.")

def main():
    print(f"[{datetime.now().isoformat()}] Starting Green Fay database backup...")
    if DATABASE_URL.startswith('sqlite'):
        path = DATABASE_URL.replace('sqlite:///', '').replace('sqlite://', '').lstrip('/')
        if not path or path == ':memory:':
            print("Cannot backup in-memory database.")
            sys.exit(0)
        backup_sqlite(path)
    else:
        backup_postgres(DATABASE_URL)
    cleanup_old_backups()

if __name__ == '__main__':
    main()

