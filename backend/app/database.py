import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./uftb_meals.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def apply_compatibility_migrations() -> None:
    """Keep pre-Alembic local databases usable after model additions."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "is_meal_member" not in columns:
        statement = (
            "ALTER TABLE users ADD COLUMN is_meal_member BOOLEAN NOT NULL DEFAULT TRUE"
            if not DATABASE_URL.startswith("sqlite")
            else "ALTER TABLE users ADD COLUMN is_meal_member BOOLEAN NOT NULL DEFAULT 1"
        )
        with engine.begin() as connection:
            connection.execute(text(statement))
    if "member_type" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN member_type VARCHAR(15) NOT NULL DEFAULT 'hostel_resident'"))
    if "address_or_identity_note" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN address_or_identity_note TEXT"))
    if "registration_controls" in inspector.get_table_names():
        control_columns = {column["name"] for column in inspector.get_columns("registration_controls")}
        if "max_registrations" not in control_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE registration_controls ADD COLUMN max_registrations INTEGER"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
