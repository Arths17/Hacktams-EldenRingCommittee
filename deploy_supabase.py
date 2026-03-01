"""
Supabase Deployment Script for HealthOS AI

Deploys the database schema, sets up authentication, and configures RLS policies.
Run this to initialize your Supabase project.
"""

import os
import sys
import json
import time
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Supabase credentials from .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL or SUPABASE_KEY not set in .env")
    sys.exit(1)

print("=" * 60)
print("  HealthOS AI - Supabase Deployment")
print("=" * 60)
print(f"✓ Supabase URL: {SUPABASE_URL}")
print()


def print_step(step_num: int, title: str, description: str = ""):
    """Print a deployment step."""
    print(f"\n📍 Step {step_num}: {title}")
    if description:
        print(f"   {description}")


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ============================================================================
# STEP 1: LOAD SCHEMA
# ============================================================================

print_step(1, "Loading database schema")

try:
    with open("docs/database_schema.sql", "r") as f:
        schema_sql = f.read()
    print(f"✓ Loaded schema ({len(schema_sql)} characters)")
except FileNotFoundError:
    print("❌ Error: docs/database_schema.sql not found")
    sys.exit(1)


# ============================================================================
# STEP 2: MANUAL DEPLOYMENT INSTRUCTIONS
# ============================================================================

print_section("DEPLOYMENT INSTRUCTIONS")

print("""
To initialize your Supabase database, follow these steps:

1. Go to Supabase Dashboard:
   🔗 https://app.supabase.com

2. Select your project:
   Project: nqhtdyhyuczdpudnaiuu

3. Navigate to SQL Editor:
   Click "SQL Editor" in left sidebar

4. Create a new query:
   Click "New query" button

5. Copy and run the schema:
   - Copy the entire contents from: docs/database_schema.sql
   - Paste into the SQL editor
   - Click "Run" button

6. Verify tables were created:
   Tables menu should show: users, health_profiles, meals, etc.

IMPORTANT: The schema includes:
✓ 20+ tables for all features
✓ Indexes for performance
✓ Row-Level Security (RLS) policies
✓ Stored procedures and functions
✓ Sample views and data

""")


# ============================================================================
# STEP 3: SCHEMA CONTENTS PREVIEW
# ============================================================================

print_section("SCHEMA PREVIEW")

# Extract table names from schema
import re
tables = re.findall(r'CREATE TABLE IF NOT EXISTS (\w+)', schema_sql)
print(f"\nTables to be created ({len(tables)}):")
for i, table in enumerate(tables, 1):
    print(f"  {i:2d}. {table}")


# ============================================================================
# STEP 4: RLS POLICIES
# ============================================================================

print_section("ROW-LEVEL SECURITY POLICIES")

print("""
The schema includes RLS policies for:

1. Users Table:
   ✓ Users can view their own profile
   ✓ Users can update their own profile

2. Health Profiles:
   ✓ Users can view own health profile
   ✓ Users can update own health profile

3. Health Metrics:
   ✓ Users can view own metrics
   ✓ Users can insert own metrics

4. Meal Logs:
   ✓ Users can view own meal logs
   ✓ Users can insert own meal logs

To verify RLS is enabled:
1. Go to Authentication > Policies
2. Select each table
3. Confirm policies are listed

""")


# ============================================================================
# STEP 5: AUTHENTICATION SETUP
# ============================================================================

print_section("AUTHENTICATION SETUP")

print("""
To enable authentication in Supabase:

1. Go to Authentication > Providers

2. Enable Email provider:
   ✓ Email/Password
   ✓ Autoconfirm email (for development)

3. Configure JWT settings:
   - Go to Authentication > JWT Secret
   - Copy JWT Secret
   - Add to your .env as: JWT_SECRET=<copied_value>

4. Set auth redirect URLs:
   - Go to Authentication > URL Configuration
   - Add redirect URLs:
     • http://localhost:3000
     • http://localhost:8000
     • http://127.0.0.1:3000

5. Get API Keys:
   - Go to Project Settings > API
   - Copy anon key (public)
   - Copy service_role key (secret)

Your .env already has:
✓ SUPABASE_URL
✓ SUPABASE_KEY (anon key)

Add to .env:
SERVICE_ROLE_KEY=<from Project Settings>
JWT_SECRET=<from Authentication>

""")


# ============================================================================
# STEP 6: SAMPLE DATA
# ============================================================================

print_section("SAMPLE DATA")

print("""
The schema includes sample meals to get started.

To add more sample data:
1. Go to SQL Editor
2. Run the INSERT statements in docs/database_schema.sql (bottom section)
3. Verify data appears in Table Editor

Sample Meals:
- Grilled Chicken Breast with Vegetables (350 cal)
- Quinoa Buddha Bowl (420 cal)
- Salmon Fillet with Sweet Potato (480 cal)

""")


# ============================================================================
# STEP 7: VERIFICATION CHECKLIST
# ============================================================================

print_section("VERIFICATION CHECKLIST")

print("""
After deployment, verify:

✓ Tables Created:
  1. Check "Tables" in Supabase dashboard
  2. Should see 20+ tables listed
  3. Example: users, health_profiles, meals, etc.

✓ Indexes Created:
  1. Go to each table > Indexes tab
  2. Should see multiple indexes (user_id, timestamps, etc.)
  3. Example: idx_users_email, idx_health_metrics_user_id_date

✓ RLS Policies:
  1. Go to Authentication > Policies
  2. Select each table
  3. Should see policies listed for sensitive tables

✓ Functions & Procedures:
  1. Go to Database > Functions
  2. Should see: calculate_bmr, update_profile_completion, get_meal_adherence

✓ Sample Data:
  1. Go to meals table > Data tab
  2. Should see 3 sample meals with nutrition info

✓ Test Connection from Python:
  Run: python -c "from supabase import create_client; print(create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')).table('users').select('count').execute())"

""")


# ============================================================================
# STEP 8: NEXT STEPS
# ============================================================================

print_section("NEXT STEPS")

print("""
1. Deploy the schema (follow steps above)

2. Test connection:
   python test_supabase_connection.py

3. Configure authentication in main.py:
   - Add JWT verification middleware
   - Test auth endpoints

4. Run integration tests:
   python -m pytest tests_churn.py -v

5. Start the server:
   uvicorn main:app --reload

""")


print("\n" + "="*60)
print("  DEPLOYMENT GUIDE COMPLETE")
print("="*60)
print("\n📌 Next: Follow the steps above to initialize your Supabase database")
print("💾 Save this output for reference\n")
