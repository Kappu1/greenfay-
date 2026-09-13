#!/usr/bin/env python3
import os, sys, shutil, subprocess

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./greenfay.db')

def restore_sqlite(backup_file: str, target_db: str):
    if not os.path.exists(backup_file):
        print(f"[ERROR] Backup file '{backup_file}' does not exist.")
        sys.exit(1)
    
    # Create safety backup of existing live db before overwrite
    if os.path.exists(target_db):
        safety_path = f"{target_db}.pre_restore_safety"
        shutil.copy2(target_db, safety_path)
        print(f"[INFO] Created pre-restore safety copy at: {safety_path}")

    shutil.copy2(backup_file, target_db)
    print(f"[SUCCESS] Database successfully restored from '{backup_file}' to '{target_db}'")

def restore_postgres(backup_file: str, url: str):
    if not os.path.exists(backup_file):
        print(f"[ERROR] Backup file '{backup_file}' does not exist.")
        sys.exit(1)
    cmd = ['psql', url, '-f', backup_file]
    try:
        subprocess.run(cmd, check=True)
        print(f"[SUCCESS] PostgreSQL database restored from '{backup_file}'")
    except Exception as e:
        print(f"[ERROR] psql restore failed: {str(e)}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/restore_db.py <path_to_backup_file>")
        sys.exit(1)
    
    backup_file = sys.argv[1]
    if DATABASE_URL.startswith('sqlite'):
        path = DATABASE_URL.replace('sqlite:///', '').replace('sqlite://', '').lstrip('/')
        restore_sqlite(backup_file, path)
    else:
        restore_postgres(backup_file, DATABASE_URL)

if __name__ == '__main__':
    main()

