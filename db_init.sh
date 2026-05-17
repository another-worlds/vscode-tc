#!/bin/bash
# Database initialization script for Traffic Count MVP
# Usage: ./db_init.sh

set -e

DB_USER=${DB_USER:-tc_user}
DB_PASSWORD=${DB_PASSWORD:-tc_password}
DB_NAME=${DB_NAME:-traffic_count}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}

echo "Initializing Traffic Count database..."
echo "Host: $DB_HOST:$DB_PORT"
echo "Database: $DB_NAME"
echo "User: $DB_USER"

# Set PostgreSQL connection info
export PGPASSWORD=$DB_PASSWORD

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until psql -h $DB_HOST -U $DB_USER -d postgres -c "SELECT 1" 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is ready!"

# Create database if it doesn't exist
echo "Creating database $DB_NAME..."
psql -h $DB_HOST -U $DB_USER -d postgres -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || psql -h $DB_HOST -U $DB_USER -d postgres -c "CREATE DATABASE \"$DB_NAME\";"

# Run migrations
echo "Running Alembic migrations..."
alembic upgrade head

echo "Database initialization complete!"

# Optional: Load seed data
# echo "Loading initial seed data..."
# psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f /app/seed_data.sql
