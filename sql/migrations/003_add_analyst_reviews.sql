-- AstraTrace PostGIS Migration: 003_add_analyst_reviews.sql
-- SIH 2026 | Problem ID: SIH26227
-- Creates the analyst_reviews table for storing human-in-the-loop decisions and audit trails.

CREATE TABLE IF NOT EXISTS analyst_reviews (
    id SERIAL PRIMARY KEY,
    review_id VARCHAR(64) UNIQUE NOT NULL,
    target_id VARCHAR(128) NOT NULL,
    target_type VARCHAR(32) NOT NULL,
    decision VARCHAR(32) NOT NULL,
    analyst_id VARCHAR(64) NOT NULL,
    notes TEXT,
    confidence_at_review DOUBLE PRECISION NOT NULL,
    quality_status_at_review VARCHAR(32) NOT NULL,
    provenance_snapshot JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analyst_reviews_target_id ON analyst_reviews(target_id);
CREATE INDEX IF NOT EXISTS idx_analyst_reviews_decision ON analyst_reviews(decision);
CREATE INDEX IF NOT EXISTS idx_analyst_reviews_analyst_id ON analyst_reviews(analyst_id);
CREATE INDEX IF NOT EXISTS idx_analyst_reviews_created_at ON analyst_reviews(created_at);
