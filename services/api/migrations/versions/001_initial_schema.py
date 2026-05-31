"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-05-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Enable PostGIS if not already enabled
    # TimescaleDB extension should be enabled beforehand in the DB, but let's try
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis CASCADE;")

    # cameras
    op.create_table(
        'cameras',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('location_lat', sa.Float(), nullable=True),
        sa.Column('location_lng', sa.Float(), nullable=True),
        sa.Column('corridor', sa.String(length=64), nullable=True),
        sa.Column('rtsp_url', sa.Text(), nullable=True),
        sa.Column('hls_url', sa.Text(), nullable=True),
        sa.Column('readiness_grade', sa.String(length=1), nullable=True, default='B'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # zones
    op.create_table(
        'zones',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=True),
        sa.Column('zone_type', sa.String(length=32), nullable=False),
        sa.Column('threshold_s', sa.Integer(), nullable=True, default=30),
        sa.Column('corridor', sa.String(length=64), nullable=True),
        sa.Column('geojson', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # violations (Timescale hypertable, PK must include partitioning column)
    op.create_table(
        'violations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('camera_id', sa.String(length=64), nullable=True),
        sa.Column('track_id', sa.String(length=64), nullable=False),
        sa.Column('violation_type', sa.String(length=32), nullable=False),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('vehicle_class', sa.String(length=32), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True, default='DETECTED'),
        sa.Column('composite_confidence', sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column('legal_basis_code', sa.String(length=64), nullable=True),
        sa.Column('sanction_code', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "violation_type IN ('ILLEGAL_PARKING','BUSWAY_VIOLATION',"
            "'BICYCLE_LANE_VIOLATION','ILLEGAL_DROPOFF','GANJIL_GENAP')",
            name='ck_violation_type'
        ),
        # Remove foreign key constraints that might break with hypertables in some versions, or keep them if needed.
        # Actually it's fine for simple referencing from standard tables.
        sa.PrimaryKeyConstraint('id', 'start_time')
    )
    # Convert 'violations' to hypertable based on 'start_time'
    op.execute("SELECT create_hypertable('violations', 'start_time', if_not_exists => TRUE);")

    # anpr_results
    op.create_table(
        'anpr_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('violation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plate_raw', sa.String(length=32), nullable=True),
        sa.Column('plate_cleaned', sa.String(length=32), nullable=True),
        sa.Column('is_valid_format', sa.Boolean(), nullable=True, default=False),
        sa.Column('ocr_confidence', sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column('quality_score', sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column('composite_confidence', sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column('needs_human_review', sa.Boolean(), nullable=True, default=True),
        sa.Column('rejection_reason', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # evidence_packages
    op.create_table(
        'evidence_packages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('violation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('best_frame_url', sa.Text(), nullable=True),
        sa.Column('video_clip_url', sa.Text(), nullable=True),
        sa.Column('video_hash_sha256', sa.String(length=64), nullable=True),
        sa.Column('plate_crop_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # etle_submissions
    op.create_table(
        'etle_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('violation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_number', sa.String(length=64), nullable=True),
        sa.Column('officer_id', sa.String(length=64), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_mock', sa.Boolean(), nullable=True, default=True),
        sa.Column('status', sa.String(length=32), nullable=True, default='DRAFT'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_number')
    )

    # h3_hotspots (Timescale hypertable, PK must include bucket)
    op.create_table(
        'h3_hotspots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('h3_index', sa.String(length=16), nullable=False),
        sa.Column('resolution', sa.Integer(), nullable=False),
        sa.Column('bucket', sa.DateTime(timezone=True), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=True, default=0.0),
        sa.Column('count', sa.Integer(), nullable=True, default=0),
        sa.Column('corridor', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('id', 'bucket'),
        sa.UniqueConstraint('h3_index', 'resolution', 'bucket', name='uq_h3_bucket')
    )
    op.execute("SELECT create_hypertable('h3_hotspots', 'bucket', if_not_exists => TRUE);")

    # crm_reports
    op.create_table(
        'crm_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('jaki_report_id', sa.String(length=64), nullable=True),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('photo_url', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('user_id_hashed', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True, default='RECEIVED'),
        sa.Column('corroborated_violation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jaki_report_id')
    )

    # unit_dispatches
    op.create_table(
        'unit_dispatches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('violation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('unit_code', sa.String(length=64), nullable=True),
        sa.Column('corridor', sa.String(length=64), nullable=True),
        sa.Column('h3_cell', sa.String(length=16), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True, default='DISPATCHED'),
        sa.Column('dispatched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # citizen_points
    op.create_table(
        'citizen_points',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id_hashed', sa.String(length=64), nullable=False),
        sa.Column('points_total', sa.Integer(), nullable=True, default=0),
        sa.Column('reports_count', sa.Integer(), nullable=True, default=0),
        sa.Column('corroborated', sa.Integer(), nullable=True, default=0),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id_hashed')
    )

    # audit_log
    op.create_table(
        'audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('entity_type', sa.String(length=64), nullable=True),
        sa.Column('entity_id', sa.String(length=64), nullable=True),
        sa.Column('officer_id', sa.String(length=64), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create append-only rule for audit log (postgres specific)
    op.execute('''
        CREATE OR REPLACE RULE prevent_audit_log_update AS
        ON UPDATE TO audit_log DO INSTEAD NOTHING;
    ''')
    op.execute('''
        CREATE OR REPLACE RULE prevent_audit_log_delete AS
        ON DELETE TO audit_log DO INSTEAD NOTHING;
    ''')


def downgrade() -> None:
    op.execute("DROP RULE IF EXISTS prevent_audit_log_delete ON audit_log;")
    op.execute("DROP RULE IF EXISTS prevent_audit_log_update ON audit_log;")
    op.drop_table('audit_log')
    op.drop_table('citizen_points')
    op.drop_table('unit_dispatches')
    op.drop_table('crm_reports')
    op.drop_table('h3_hotspots')
    op.drop_table('etle_submissions')
    op.drop_table('evidence_packages')
    op.drop_table('anpr_results')
    op.drop_table('violations')
    op.drop_table('zones')
    op.drop_table('cameras')
