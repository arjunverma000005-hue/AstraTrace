-- AstraTrace PostGIS Migration: 004_add_audit_events.sql
-- SIH 2026 | Problem ID: SIH26227
-- Creates the audit_events table for append-oriented audit tracking of queries, change detections, reviews, verifications, and exports.

CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(64) UNIQUE NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    actor VARCHAR(64) NOT NULL,
    action VARCHAR(64) NOT NULL,
    target_id VARCHAR(128) NOT NULL,
    target_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_actor ON audit_events(actor);
CREATE INDEX IF NOT EXISTS idx_audit_events_target_id ON audit_events(target_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_status ON audit_events(status);
CREATE INDEX IF NOT EXISTS idx_audit_events_created_at ON audit_events(created_at);
