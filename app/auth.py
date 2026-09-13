from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import hashlib, hmac, os, base64, re

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    _ph = PasswordHasher()
except ImportError:
    _ph = None

from .database import get_db
from .models import User, AuditLog, Season

SECRET = os.getenv('APP_SECRET', 'change-this-in-production')

def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(400, 'Password must be at least 8 characters long')
    if not re.search(r'[A-Z]', password):
        raise HTTPException(400, 'Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', password):
        raise HTTPException(400, 'Password must contain at least one lowercase letter')
    if not re.search(r'\d', password):
        raise HTTPException(400, 'Password must contain at least one digit')

def pw_hash(password: str) -> str:
    if _ph:
        return _ph.hash(password)
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 150000)
    return base64.b64encode(salt + dk).decode()

def pw_verify(password: str, stored: str) -> bool:
    if stored.startswith('$argon2'):
        if not _ph: return False
        try:
            return _ph.verify(stored, password)
        except VerifyMismatchError:
            return False
        except Exception:
            return False
    # Legacy PBKDF2 verification
    try:
        raw = base64.b64decode(stored.encode())
        salt, expected = raw[:16], raw[16:]
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 150000)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def sign_token(user_id: int) -> str:
    now_ts = int(datetime.now(timezone.utc).timestamp())
    exp_ts = now_ts + (7 * 86400)
    payload = f'{user_id}:{exp_ts}'
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f'{payload}:{sig}'.encode()).decode()

def parse_token(token: str):
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        uid, exp, sig = raw.split(':')
        payload = f'{uid}:{exp}'
        good = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if not hmac.compare_digest(sig, good) or int(exp) < now_ts:
            return None
        return int(uid)
    except Exception:
        return None

def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get('gf_session', '')
    if not token and request.headers.get('Authorization', '').startswith('Bearer '):
        token = request.headers.get('Authorization')[7:]
    uid = parse_token(token)
    if not uid:
        raise HTTPException(401, 'Authentication required')
    u = db.get(User, uid)
    if not u or not u.active:
        raise HTTPException(401, 'Invalid or inactive user account')
    return u

def require_roles(*roles):
    def role_dependency(user: User = Depends(current_user)):
        if user.role == 'admin':
            return user
        if user.role not in roles:
            raise HTTPException(403, f"Access denied for role '{user.role}'. Required: {', '.join(roles)}")
        return user
    return role_dependency

def audit(db: Session, user: User, entity: str, entity_id: int, action: str, details: str = '', module: str = None, old_values = None, new_values = None):
    import json
    old_str = json.dumps(old_values, default=str) if isinstance(old_values, (dict, list)) else (str(old_values) if old_values else None)
    new_str = json.dumps(new_values, default=str) if isinstance(new_values, (dict, list)) else (str(new_values) if new_values else None)
    log = AuditLog(
        user_id=user.id if user else None,
        entity=entity,
        entity_id=entity_id,
        action=action,
        details=details,
        module=module or entity,
        old_values=old_str,
        new_values=new_str,
        user_name=user.name if user else 'System'
    )
    db.add(log)

def check_season_unlocked(db: Session, season_identifier):
    if not season_identifier:
        return
    q = db.query(Season)
    if isinstance(season_identifier, int) or str(season_identifier).isdigit():
        s = q.filter(Season.id == int(season_identifier)).first()
    else:
        s = q.filter(Season.name == str(season_identifier)).first()
    if s and s.status in ['Locked', 'Archived']:
        raise HTTPException(400, f"Season '{s.name}' is currently {s.status}. Modifications are locked.")

def code(prefix: str, ident: int) -> str:
    return f'{prefix}-{ident:06d}'
