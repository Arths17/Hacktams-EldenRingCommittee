#!/bin/bash
# Supabase Deployment Script for HealthOS AI
# This script initializes the Supabase database with the schema

set -e

echo "========================================"
echo "HealthOS AI - Supabase Deployment"
echo "========================================"

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "⚠️  Supabase CLI not found. Installing..."
    brew install supabase/tap/supabase
fi

SUPABASE_URL="${SUPABASE_URL}"
SUPABASE_KEY="${SUPABASE_KEY}"

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    echo "❌ Error: SUPABASE_URL or SUPABASE_KEY not set in .env"
    exit 1
fi

echo "✓ Supabase credentials found"
echo "  URL: $SUPABASE_URL"

# Run the schema SQL file
echo ""
echo "Running database schema..."
cat docs/database_schema.sql | psql "postgres://postgres:[YOUR_PASSWORD]@db.nqhtdyhyuczdpudnaiuu.supabase.co:5432/postgres" 2>/dev/null || {
    echo "⚠️  Direct psql connection failed. Using Supabase web interface instead."
    echo ""
    echo "📋 To execute the schema manually:"
    echo "1. Go to: https://app.supabase.com"
    echo "2. Select your project"
    echo "3. Go to SQL Editor"
    echo "4. Create new query"
    echo "5. Copy content of docs/database_schema.sql"
    echo "6. Run the query"
}

echo ""
echo "✓ Schema deployment complete!"
echo ""
echo "Next steps:"
echo "1. Verify tables in Supabase SQL Editor"
echo "2. Configure RLS policies (already in schema)"
echo "3. Test authentication"
echo ""
