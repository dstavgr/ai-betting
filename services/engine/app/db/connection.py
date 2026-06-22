from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings


def check_database() -> tuple[bool, str]:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        return True, "ok"
    except SQLAlchemyError as exc:
        return False, exc.__class__.__name__
    finally:
        engine.dispose()
