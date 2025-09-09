-- Initialize PostgreSQL database for Agentic API
-- This script creates the necessary extensions and initial setup

-- Create pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Create uuid extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant permissions to the user
GRANT ALL PRIVILEGES ON DATABASE ai TO ai;

-- Create schema if needed
CREATE SCHEMA IF NOT EXISTS public;
GRANT ALL ON SCHEMA public TO ai;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialized successfully with pgvector extension';
END $$;