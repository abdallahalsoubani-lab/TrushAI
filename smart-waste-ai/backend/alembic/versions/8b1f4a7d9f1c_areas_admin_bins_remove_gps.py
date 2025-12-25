"""Areas + admin bins + remove GPS fields

Revision ID: 8b1f4a7d9f1c
Revises: 7c5f3f2b2c0b
Create Date: 2025-12-24 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = '8b1f4a7d9f1c'
down_revision: Union[str, Sequence[str], None] = '7c5f3f2b2c0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "areas" not in tables:
        op.create_table(
            "areas",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_areas_name"), "areas", ["name"], unique=True)
        op.create_index(op.f("ix_areas_created_at"), "areas", ["created_at"], unique=False)
        op.create_index(op.f("ix_areas_updated_at"), "areas", ["updated_at"], unique=False)

    # Ensure default area exists
    area_id = bind.execute(text("SELECT id FROM areas WHERE name = 'default'")).scalar()
    if not area_id:
        bind.execute(
            text(
                "INSERT INTO areas (name, created_at, updated_at) "
                "VALUES (:name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"name": "default"},
        )
        area_id = bind.execute(text("SELECT id FROM areas WHERE name = 'default'")).scalar()

    if "bins" in tables:
        cols = {c["name"] for c in insp.get_columns("bins")}
        with op.batch_alter_table("bins", schema=None) as batch_op:
            if "area_id" not in cols:
                batch_op.add_column(sa.Column("area_id", sa.Integer(), nullable=True))
            if "last_seen_at" not in cols:
                batch_op.add_column(sa.Column("last_seen_at", sa.DateTime(), nullable=True))
            if "ops_status" not in cols:
                batch_op.add_column(sa.Column("ops_status", sa.String(length=20), nullable=True))
            if "ops_notes" not in cols:
                batch_op.add_column(sa.Column("ops_notes", sa.Text(), nullable=True))
            if "is_false_positive" not in cols:
                batch_op.add_column(sa.Column("is_false_positive", sa.Boolean(), nullable=True))
            if "priority_score" not in cols:
                batch_op.add_column(sa.Column("priority_score", sa.Float(), nullable=True))
            if "priority_reason" not in cols:
                batch_op.add_column(sa.Column("priority_reason", sa.Text(), nullable=True))
            if "lat" in cols:
                batch_op.drop_column("lat")
            if "lng" in cols:
                batch_op.drop_column("lng")
            if "accuracy" in cols:
                batch_op.drop_column("accuracy")

        bind.execute(text("UPDATE bins SET area_id = :area_id WHERE area_id IS NULL"), {"area_id": area_id})
        bind.execute(text("UPDATE bins SET last_seen_at = CURRENT_TIMESTAMP WHERE last_seen_at IS NULL"))
        bind.execute(text("UPDATE bins SET ops_status = 'NEW' WHERE ops_status IS NULL"))
        bind.execute(text("UPDATE bins SET is_false_positive = 0 WHERE is_false_positive IS NULL"))
        bind.execute(text("UPDATE bins SET priority_score = 0 WHERE priority_score IS NULL"))

        with op.batch_alter_table("bins", schema=None) as batch_op:
            batch_op.alter_column("area_id", nullable=False)
            batch_op.alter_column("last_seen_at", nullable=False)
            batch_op.alter_column("ops_status", nullable=False)
            batch_op.alter_column("is_false_positive", nullable=False)
            batch_op.alter_column("priority_score", nullable=False)
            batch_op.create_index(batch_op.f("ix_bins_area_id"), ["area_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_bins_ops_status"), ["ops_status"], unique=False)
            batch_op.create_index(batch_op.f("ix_bins_priority_score"), ["priority_score"], unique=False)
            batch_op.create_foreign_key("fk_bins_area_id", "areas", ["area_id"], ["id"], ondelete="CASCADE")

    if "captures" in tables:
        cols = {c["name"] for c in insp.get_columns("captures")}
        with op.batch_alter_table("captures", schema=None) as batch_op:
            if "area_id" not in cols:
                batch_op.add_column(sa.Column("area_id", sa.Integer(), nullable=True))
            if "lat" in cols:
                batch_op.drop_column("lat")
            if "lng" in cols:
                batch_op.drop_column("lng")
            if "accuracy" in cols:
                batch_op.drop_column("accuracy")
        bind.execute(text("UPDATE captures SET area_id = :area_id WHERE area_id IS NULL"), {"area_id": area_id})
        with op.batch_alter_table("captures", schema=None) as batch_op:
            batch_op.alter_column("area_id", nullable=False)
            batch_op.create_index(batch_op.f("ix_captures_area_id"), ["area_id"], unique=False)
            batch_op.create_foreign_key("fk_captures_area_id", "areas", ["area_id"], ["id"], ondelete="CASCADE")

    if "bin_events" not in tables:
        op.create_table(
            "bin_events",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("bin_id", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=30), nullable=False),
            sa.Column("from_status", sa.String(length=20), nullable=True),
            sa.Column("to_status", sa.String(length=20), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["bin_id"], ["bins.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_bin_events_bin_id"), "bin_events", ["bin_id"], unique=False)
        op.create_index(op.f("ix_bin_events_event_type"), "bin_events", ["event_type"], unique=False)
        op.create_index(op.f("ix_bin_events_created_at"), "bin_events", ["created_at"], unique=False)

    if "gps_samples" in tables:
        op.drop_table("gps_samples")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "gps_samples" not in tables:
        op.create_table(
            "gps_samples",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("session_id", sa.String(length=64), nullable=False),
            sa.Column("device_id", sa.String(length=64), nullable=False),
            sa.Column("lat", sa.Float(), nullable=False),
            sa.Column("lng", sa.Float(), nullable=False),
            sa.Column("accuracy", sa.Float(), nullable=False),
            sa.Column("heading", sa.Float(), nullable=True),
            sa.Column("speed", sa.Float(), nullable=True),
            sa.Column("ts_client", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_gps_samples_session_id"), "gps_samples", ["session_id"], unique=False)
        op.create_index(op.f("ix_gps_samples_device_id"), "gps_samples", ["device_id"], unique=False)
        op.create_index(op.f("ix_gps_samples_created_at"), "gps_samples", ["created_at"], unique=False)

    if "bin_events" in tables:
        op.drop_index(op.f("ix_bin_events_created_at"), table_name="bin_events")
        op.drop_index(op.f("ix_bin_events_event_type"), table_name="bin_events")
        op.drop_index(op.f("ix_bin_events_bin_id"), table_name="bin_events")
        op.drop_table("bin_events")

    if "captures" in tables:
        cols = {c["name"] for c in insp.get_columns("captures")}
        with op.batch_alter_table("captures", schema=None) as batch_op:
            if "area_id" in cols:
                batch_op.drop_constraint("fk_captures_area_id", type_="foreignkey")
                batch_op.drop_index(batch_op.f("ix_captures_area_id"))
                batch_op.drop_column("area_id")

    if "bins" in tables:
        cols = {c["name"] for c in insp.get_columns("bins")}
        with op.batch_alter_table("bins", schema=None) as batch_op:
            if "area_id" in cols:
                batch_op.drop_constraint("fk_bins_area_id", type_="foreignkey")
                batch_op.drop_index(batch_op.f("ix_bins_area_id"))
                batch_op.drop_column("area_id")
            if "ops_status" in cols:
                batch_op.drop_index(batch_op.f("ix_bins_ops_status"))
                batch_op.drop_column("ops_status")
            if "priority_score" in cols:
                batch_op.drop_index(batch_op.f("ix_bins_priority_score"))
                batch_op.drop_column("priority_score")
            if "ops_notes" in cols:
                batch_op.drop_column("ops_notes")
            if "is_false_positive" in cols:
                batch_op.drop_column("is_false_positive")
            if "priority_reason" in cols:
                batch_op.drop_column("priority_reason")
            if "last_seen_at" in cols:
                batch_op.drop_column("last_seen_at")

    if "areas" in tables:
        op.drop_index(op.f("ix_areas_updated_at"), table_name="areas")
        op.drop_index(op.f("ix_areas_created_at"), table_name="areas")
        op.drop_index(op.f("ix_areas_name"), table_name="areas")
        op.drop_table("areas")
