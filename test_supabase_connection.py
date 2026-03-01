"""
Test Supabase connection and verify database setup.

Run this after deploying the schema to verify everything is working.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("  Supabase Connection Test")
print("=" * 60)
print()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL or SUPABASE_KEY not set in .env")
    sys.exit(1)

print(f"✓ Supabase URL: {SUPABASE_URL}")
print()

# Try to connect
try:
    from supabase import create_client
    
    print("📍 Connecting to Supabase...")
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✓ Connection successful!")
    print()
    
    # Test 1: Check users table exists
    print("📍 Test 1: Checking users table...")
    result = sb.table("users").select("count").execute()
    print(f"✓ Users table exists (count: {len(result.data)})")
    
    # Test 2: Check health_profiles table
    print("📍 Test 2: Checking health_profiles table...")
    result = sb.table("health_profiles").select("count").execute()
    print(f"✓ Health profiles table exists")
    
    # Test 3: Check meals table
    print("📍 Test 3: Checking meals table...")
    result = sb.table("meals").select("*").execute()
    print(f"✓ Meals table exists ({len(result.data)} sample meals)")
    for meal in result.data:
        if isinstance(meal, dict):
            print(f"  - {meal.get('name', 'Unknown')}: {meal.get('calories', 0)} cal")  # type: ignore[union-attr]
    
    # Test 4: Check user_events table
    print("📍 Test 4: Checking user_events table...")
    result = sb.table("user_events").select("count").execute()
    print(f"✓ User events table exists")
    
    # Test 5: Check churn_features table
    print("📍 Test 5: Checking churn_features table...")
    result = sb.table("churn_features").select("count").execute()
    print(f"✓ Churn features table exists")
    
    print()
    print("="*60)
    print("✓ ALL TESTS PASSED")
    print("="*60)
    print()
    print("Your Supabase database is ready to use!")
    print()
    print("Next steps:")
    print("1. Start the API: uvicorn main:app --reload")
    print("2. Test endpoints: curl http://localhost:8000/health")
    print("3. Run tests: python -m pytest test_churn_simple.py -v")
    print()

except ImportError:
    print("❌ Error: supabase-py not installed")
    print("   Run: pip install supabase")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {str(e)}")
    print()
    print("Troubleshooting:")
    print("1. Verify SUPABASE_URL and SUPABASE_KEY in .env")
    print("2. Ensure database schema has been deployed")
    print("3. Check Supabase status: https://status.supabase.com")
    sys.exit(1)
