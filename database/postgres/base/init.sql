-- DROP SCHEMA IF EXISTS app CASCADE;
-- DROP SCHEMA IF EXISTS audit CASCADE;
-- DROP FUNCTION IF EXISTS app.update_updated_at_column();
-- PostgreSQL initialization script aligned with application models
-- Runs once when the database is first created

-- Extensions for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Schema for application tables
CREATE SCHEMA IF NOT EXISTS app;
GRANT ALL PRIVILEGES ON SCHEMA app TO postgres;

-- Heroes table
CREATE TABLE IF NOT EXISTS app.heroes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    level INT DEFAULT 1,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_heroes_name ON app.heroes(name);
CREATE INDEX IF NOT EXISTS idx_heroes_level ON app.heroes(level);

-- Users table
CREATE TABLE IF NOT EXISTS app.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(10) NOT NULL DEFAULT 'young' CHECK (type IN ('young', 'old')),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_name ON app.users(name);
CREATE INDEX IF NOT EXISTS idx_users_type ON app.users(type);

-- One-day classes table
CREATE TABLE IF NOT EXISTS app.classes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    creator_id UUID NOT NULL,
    category VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    start_time VARCHAR(100) NOT NULL,
    duration_minutes INT NOT NULL,
    capacity INT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Enrollments table
CREATE TABLE IF NOT EXISTS app.enrollments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    class_id UUID NOT NULL,
    user_id UUID NOT NULL,
    applied_date VARCHAR(50) NOT NULL,
    headcount INT NOT NULL
);

-- Seed data for heroes (optional)
INSERT INTO app.heroes (name, description, level) VALUES
    ('Hero Alpha', 'The first hero', 1),
    ('Hero Beta', 'The second hero', 2),
    ('Hero Gamma', 'The third hero', 3)
ON CONFLICT DO NOTHING;
