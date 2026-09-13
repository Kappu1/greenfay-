from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.database import get_db
from app.models import User
from app.auth import current_user, require_roles, pw_hash, pw_verify, validate_password_strength, audit

router = APIRouter()

@router.get('/users')
def list_users(db: Session = Depends(get_db), user: User = Depends(require_roles('admin'))):
    users = db.query(User).order_by(User.id.asc()).all()
    return [
        {
            'id': u.id,
            'name': u.name,
            'email': u.email,
            'role': u.role,
            'active': u.active,
            'last_login_at': str(u.last_login_at) if u.last_login_at else None,
            'created_at': str(u.created_at) if u.created_at else None
        }
        for u in users
    ]

@router.post('/users')
async def create_user(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_roles('admin'))):
    d = await request.json()
    email = d.get('email', '').strip().lower()
    name = d.get('name', '').strip()
    role = d.get('role', 'operator').strip().lower()
    password = d.get('password', '')

    if not email or not name:
        raise HTTPException(400, 'Name and email are required')
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, 'User with this email already exists')
    
    validate_password_strength(password)
    
    u = User(
        email=email,
        name=name,
        role=role,
        password_hash=pw_hash(password),
        active=True,
        password_changed_at=datetime.utcnow()
    )
    db.add(u)
    db.flush()
    audit(db, admin, 'User', u.id, 'CREATE', f"Created user {u.email} ({u.role})", module='Users')
    db.commit()
    return {'id': u.id, 'email': u.email, 'name': u.name, 'role': u.role}

@router.put('/users/{id}')
async def update_user(id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_roles('admin'))):
    d = await request.json()
    u = db.get(User, id)
    if not u:
        raise HTTPException(404, 'User not found')

    old_vals = {'name': u.name, 'role': u.role, 'active': u.active}
    if 'name' in d and d['name'].strip():
        u.name = d['name'].strip()
    if 'role' in d and d['role'].strip():
        u.role = d['role'].strip().lower()
    if 'active' in d:
        u.active = bool(d['active'])
        if not u.active and u.id == admin.id:
            raise HTTPException(400, 'Cannot deactivate your own admin account')

    new_vals = {'name': u.name, 'role': u.role, 'active': u.active}
    audit(db, admin, 'User', u.id, 'UPDATE', f"Updated user {u.email}", module='Users', old_values=old_vals, new_values=new_vals)
    db.commit()
    return {'ok': True, 'id': u.id}

@router.post('/users/{id}/reset-password')
async def admin_reset_password(id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_roles('admin'))):
    d = await request.json()
    new_pw = d.get('new_password', '')
    validate_password_strength(new_pw)

    u = db.get(User, id)
    if not u:
        raise HTTPException(404, 'User not found')

    u.password_hash = pw_hash(new_pw)
    u.password_changed_at = datetime.utcnow()
    u.failed_login_attempts = 0
    u.locked_until = None
    u.must_change_password = True

    audit(db, admin, 'User', u.id, 'RESET_PASSWORD', f"Admin reset password for {u.email}", module='Users')
    db.commit()
    return {'ok': True, 'message': 'Password reset successfully'}

@router.post('/users/change-password')
async def user_change_password(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    d = await request.json()
    current_pw = d.get('current_password', '')
    new_pw = d.get('new_password', '')

    if not pw_verify(current_pw, user.password_hash):
        raise HTTPException(400, 'Current password incorrect')

    validate_password_strength(new_pw)

    user.password_hash = pw_hash(new_pw)
    user.password_changed_at = datetime.utcnow()
    user.must_change_password = False

    audit(db, user, 'User', user.id, 'CHANGE_PASSWORD', 'User changed their own password', module='Users')
    db.commit()
    return {'ok': True, 'message': 'Password updated successfully'}
