-- NaijaIntel Database Schema
-- Dev: SQLite | Production: PostgreSQL (syntax is compatible)
-- Run: sqlite3 naijaintel.db < naijaintel_migrations.sql

PRAGMA foreign_keys = ON;

-- ── 1. SOURCES ────────────────────────────────────────────────────────────────
-- One row per feed outlet (Premium Times RSS, GNews API, etc.)
CREATE TABLE IF NOT EXISTS sources (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       VARCHAR(100) NOT NULL,          -- e.g. "Premium Times"
    type       VARCHAR(20)  NOT NULL,          -- "rss" | "api"
    url        TEXT         NOT NULL,          -- feed URL
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ── 2. ARTICLES ───────────────────────────────────────────────────────────────
-- Immutable raw store. Never update a row — only insert.
CREATE TABLE IF NOT EXISTS articles (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id          INTEGER      NOT NULL REFERENCES sources(id),
    title              VARCHAR(500) NOT NULL,
    body               TEXT,                  -- full article text (via newspaper3k)
    url                TEXT         NOT NULL,
    content_hash       VARCHAR(64)  NOT NULL UNIQUE,  -- MD5 of URL for dedup
    published_at       TIMESTAMP,
    processed          BOOLEAN      DEFAULT FALSE,     -- has LLM seen this?
    extraction_status  VARCHAR(20)  DEFAULT 'pending', -- pending | success | failed | irrelevant
    created_at         TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_articles_processed
    ON articles(processed, extraction_status);  -- pipeline worker queries this constantly

CREATE INDEX IF NOT EXISTS idx_articles_published
    ON articles(published_at DESC);

-- ── 3. EVENT_TYPES ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS event_types (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE   -- kidnapping | banditry | armed_robbery | etc.
);

-- Seed core security event types
INSERT OR IGNORE INTO event_types (name) VALUES
    ('kidnapping'),
    ('banditry'),
    ('armed_robbery'),
    ('terrorist_attack'),
    ('communal_clash'),
    ('assassination'),
    ('jail_break'),
    ('pipeline_vandalism');

-- ── 4. STATES ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS states (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE
);

-- All 36 Nigerian states + FCT
INSERT OR IGNORE INTO states (name) VALUES
    ('Abia'), ('Adamawa'), ('Akwa Ibom'), ('Anambra'), ('Bauchi'),
    ('Bayelsa'), ('Benue'), ('Borno'), ('Cross River'), ('Delta'),
    ('Ebonyi'), ('Edo'), ('Ekiti'), ('Enugu'), ('Gombe'),
    ('Imo'), ('Jigawa'), ('Kaduna'), ('Kano'), ('Katsina'),
    ('Kebbi'), ('Kogi'), ('Kwara'), ('Lagos'), ('Nasarawa'),
    ('Niger'), ('Ogun'), ('Ondo'), ('Osun'), ('Oyo'),
    ('Plateau'), ('Rivers'), ('Sokoto'), ('Taraba'), ('Yobe'),
    ('Zamfara'), ('FCT Abuja');

-- ── 5. LOCATIONS ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS locations (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id  INTEGER     NOT NULL REFERENCES states(id),
    name      VARCHAR(200) NOT NULL,       -- e.g. "Abuja-Kaduna Highway"
    latitude  REAL,
    longitude REAL
);

CREATE INDEX IF NOT EXISTS idx_locations_state
    ON locations(state_id);

-- ── 6. EVENTS ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type_id INTEGER NOT NULL REFERENCES event_types(id),
    location_id   INTEGER NOT NULL REFERENCES locations(id),
    event_date    DATE,
    confidence    REAL    DEFAULT 0.0,    -- LLM confidence score 0.0 to 1.0
    summary       TEXT,                   -- LLM-generated one-liner
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_date
    ON events(event_date DESC);

CREATE INDEX IF NOT EXISTS idx_events_type
    ON events(event_type_id);

CREATE INDEX IF NOT EXISTS idx_events_location
    ON events(location_id);

-- ── 7. EVENT_STATISTICS ───────────────────────────────────────────────────────
-- 1-to-1 with events. Separated to keep events table lean.
CREATE TABLE IF NOT EXISTS event_statistics (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL UNIQUE REFERENCES events(id), -- UNIQUE enforces 1-to-1
    killed   INTEGER DEFAULT 0,
    injured  INTEGER DEFAULT 0,
    abducted INTEGER DEFAULT 0
);

-- ── 8. EVENT_SOURCES ──────────────────────────────────────────────────────────
-- Many-to-many bridge: multiple articles can back one event
-- This is how you handle Punch + Vanguard + GNews covering the same incident
CREATE TABLE IF NOT EXISTS event_sources (
    event_id   INTEGER NOT NULL REFERENCES events(id),
    article_id INTEGER NOT NULL REFERENCES articles(id),
    PRIMARY KEY (event_id, article_id)   -- composite PK prevents duplicate links
);
