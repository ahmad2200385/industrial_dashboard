from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from core.config import settings

connect_args = {'check_same_thread': False} if settings.DATABASE_URL.startswith('sqlite') else {}
engine_kwargs = {
    'pool_pre_ping': True,
    'future': True,
}
if connect_args:
    engine_kwargs['connect_args'] = connect_args

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
Base = declarative_base()
