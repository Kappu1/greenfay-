from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from .models import Base
import os
import time

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./greenfay.db')

# Automatically normalize PostgreSQL scheme to psycopg v3 driver if needed
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
elif DATABASE_URL.startswith('postgresql://') and not DATABASE_URL.startswith('postgresql+'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)

engine_kwargs = {}
if DATABASE_URL.startswith('sqlite'):
    engine_kwargs['connect_args'] = {'check_same_thread': False}
    if ':memory:' in DATABASE_URL:
        engine_kwargs['poolclass'] = StaticPool
else:
    # Production PostgreSQL connection pool settings
    engine_kwargs['pool_size'] = int(os.getenv('DB_POOL_SIZE', '10'))
    engine_kwargs['max_overflow'] = int(os.getenv('DB_MAX_OVERFLOW', '20'))
    engine_kwargs['pool_pre_ping'] = True
    engine_kwargs['pool_recycle'] = 1800

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connectivity():
    start = time.time()
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    latency_ms = round((time.time() - start) * 1000, 2)
    return {'status': 'ok', 'latency_ms': latency_ms, 'dialect': engine.dialect.name}
