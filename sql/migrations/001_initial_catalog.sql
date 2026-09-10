-- Migration 001: Initial Catalog Schema (Scenes and Tiles)
-- AstraTrace | SIH 2026 | Problem ID: SIH26227

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS scenes (
    scene_id VARCHAR(128) PRIMARY KEY,
    source_uri TEXT NOT NULL,
    sensor VARCHAR(64) NOT NULL,
    collection VARCHAR(128) NOT NULL DEFAULT 'demo_archive',
    acquired_at TIMESTAMPTZ NOT NULL,
    crs VARCHAR(64) NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    bands INTEGER NOT NULL,
    resolution_meters DOUBLE PRECISION DEFAULT 10.0,
    min_lon DOUBLE PRECISION NOT NULL,
    min_lat DOUBLE PRECISION NOT NULL,
    max_lon DOUBLE PRECISION NOT NULL,
    max_lat DOUBLE PRECISION NOT NULL,
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    manifest_path TEXT NOT NULL,
    tiles_count INTEGER NOT NULL,
    tile_size INTEGER NOT NULL DEFAULT 256,
    overlap INTEGER NOT NULL DEFAULT 25,
    status VARCHAR(32) NOT NULL DEFAULT 'INDEXED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tiles (
    tile_id VARCHAR(160) PRIMARY KEY,
    scene_id VARCHAR(128) NOT NULL REFERENCES scenes(scene_id) ON DELETE CASCADE,
    tile_index INTEGER NOT NULL,
    path TEXT NOT NULL,
    min_lon DOUBLE PRECISION NOT NULL,
    min_lat DOUBLE PRECISION NOT NULL,
    max_lon DOUBLE PRECISION NOT NULL,
    max_lat DOUBLE PRECISION NOT NULL,
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    col_off INTEGER NOT NULL,
    row_off INTEGER NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    cloud_cover_percent DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    nodata_percent DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scenes_geom ON scenes USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_tiles_geom ON tiles USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_scenes_acquired_at ON scenes (acquired_at);
CREATE INDEX IF NOT EXISTS idx_scenes_sensor_date ON scenes (sensor, acquired_at);
CREATE INDEX IF NOT EXISTS idx_scenes_collection ON scenes (collection);
CREATE INDEX IF NOT EXISTS idx_tiles_scene_id ON tiles (scene_id);
CREATE INDEX IF NOT EXISTS idx_tiles_quality ON tiles (cloud_cover_percent, nodata_percent);
