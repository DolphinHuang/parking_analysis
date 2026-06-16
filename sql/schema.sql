CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS parking_status_raw (
    collected_at_utc TIMESTAMPTZ NOT NULL,
    section_id TEXT NOT NULL,
    ps_id TEXT NOT NULL,
    ps_type SMALLINT,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    status SMALLINT,
    county_code TEXT,
    agency_codes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (collected_at_utc, section_id, ps_id)
);

SELECT create_hypertable(
    'parking_status_raw',
    'collected_at_utc',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

CREATE INDEX IF NOT EXISTS idx_parking_status_raw_ps_id_time
ON parking_status_raw (ps_id, collected_at_utc DESC);
