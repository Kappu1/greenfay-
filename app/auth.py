from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import hashlib, hmac, os, base64

from .database import get_db
from .models import User, AuditLog

SECRET = os.getenv('APP_SECRET', 'change-this-in-production')

def pw_hash(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 150000)
    return base64.b64encode(salt + dk).decode()

def pw_verify(password: str, stored: str) -> bool:
    raw = base64.b64decode(stored.encode())
    salt, expected = raw[:16], raw[16:]
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 150000)
    return hmac.compare_digest(actual, expected)

def sign_token(user_id: int) -> str:
    payload = f'{user_id}:{int((datetime.utcnow()+timedelta(days=7)).timestamp())}'
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f'{payload}:{sig}'.encode()).decode()

def parse_token(token: str):
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        uid, exp, sig = raw.split(':')
        payload = f'{uid}:{exp}'
        good = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, good) or int(exp) < int(datetime.utcnow().timestamp()): return None
        return int(uid)
    except Exception:
        return None

def current_user(request: Request, db: Session = Depends(get_db)):
    uid = parse_token(request.cookies.get('gf_session',''))
    if not uid: raise HTTPException(401, 'Authentication required')
    u = db.get(User, uid)
    if not u or not u.active: raise HTTPException(401, 'Invalid user')
    return u

def audit(db, user, entity, entity_id, action, details=''):
    db.add(AuditLog(user_id=user.id, entity=entity, entity_id=entity_id, action=action, details=details, user_name=user.name))

def code(prefix, ident): return f'{prefix}-{ident:06d}'
