-- PostgreSQL initialization script for Wadeulwadeul Heroes
-- This script runs only once when the database is first created

-- Create additional database if needed
-- CREATE DATABASE wadeulwadeul_dev;

-- Connect to the main database
\c wadeulwadeul_db;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS audit;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA app TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA audit TO postgres;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION app.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create heroes table
CREATE TABLE IF NOT EXISTS app.heroes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    level INT DEFAULT 1,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create users table
CREATE TABLE IF NOT EXISTS app.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(10) NOT NULL DEFAULT 'young' CHECK (type IN ('young', 'old')),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit.logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(255) NOT NULL,
    operation VARCHAR(50) NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_by VARCHAR(255),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_heroes_name ON app.heroes(name);
CREATE INDEX IF NOT EXISTS idx_heroes_level ON app.heroes(level);
CREATE INDEX IF NOT EXISTS idx_users_email ON app.users(email);
CREATE INDEX IF NOT EXISTS idx_users_name ON app.users(name);
CREATE INDEX IF NOT EXISTS idx_users_type ON app.users(type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_table ON audit.logs(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_logs_changed_at ON audit.logs(changed_at);

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_heroes_updated_at ON app.heroes;
CREATE TRIGGER update_heroes_updated_at
    BEFORE UPDATE ON app.heroes
    FOR EACH ROW
    EXECUTE FUNCTION app.update_updated_at_column();

DROP TRIGGER IF EXISTS update_users_updated_at ON app.users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON app.users
    FOR EACH ROW
    EXECUTE FUNCTION app.update_updated_at_column();

-- Insert sample data (optional)
INSERT INTO app.heroes (name, description, level) VALUES
    ('Hero Alpha', 'The first hero', 1),
    ('Hero Beta', 'The second hero', 2),
    ('Hero Gamma', 'The third hero', 3)
ON CONFLICT DO NOTHING;

-- Create read-only user (optional, for reporting)
-- CREATE USER readonly_user WITH PASSWORD 'readonly123';
-- GRANT CONNECT ON DATABASE wadeulwadeul_db TO readonly_user;
-- GRANT USAGE ON SCHEMA app TO readonly_user;
-- GRANT SELECT ON ALL TABLES IN SCHEMA app TO readonly_user;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT SELECT ON TABLES TO readonly_user;

COMMENT ON TABLE app.heroes IS 'Main heroes table for the application';
COMMENT ON TABLE audit.logs IS 'Audit log table for tracking changes';

-- Print success message
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully!';
END $$;
