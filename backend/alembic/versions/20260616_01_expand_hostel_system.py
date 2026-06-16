"""expand hostel meal system

Revision ID: 20260616_01
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

from app.models import Base


revision = "20260616_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()
    if "users" in tables and "is_meal_member" not in {column["name"] for column in inspector.get_columns("users")}:
        op.add_column("users", sa.Column("is_meal_member", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "users" in tables and "member_type" not in {column["name"] for column in inspector.get_columns("users")}:
        op.add_column("users", sa.Column("member_type", sa.String(length=15), nullable=False, server_default="hostel_resident"))
    if "users" in tables and "address_or_identity_note" not in {column["name"] for column in inspector.get_columns("users")}:
        op.add_column("users", sa.Column("address_or_identity_note", sa.Text(), nullable=True))
    if "registration_controls" in tables and "max_registrations" not in {column["name"] for column in inspector.get_columns("registration_controls")}:
        op.add_column("registration_controls", sa.Column("max_registrations", sa.Integer(), nullable=True))
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    for table in ("weekly_notices", "attendance", "payments", "meal_members", "weekly_cycles"):
        op.drop_table(table)
    if "registration_controls" in inspect(op.get_bind()).get_table_names():
        with op.batch_alter_table("registration_controls") as batch:
            batch.drop_column("max_registrations")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("is_meal_member")
        batch.drop_column("member_type")
        batch.drop_column("address_or_identity_note")
