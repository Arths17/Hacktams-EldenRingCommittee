import os
from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    print("✓ Supabase connection successful")
    print(f"URL: {os.environ['SUPABASE_URL']}")
    print("USE_SUPABASE would be: True")
    
    # Test if users table exists
    try:
        result = sb.table("users").select("*").limit(1).execute()
        print(f"✓ Users table exists (found {len(result.data)} records)")
    except Exception as e:
        print(f"⚠ Users table issue: {e}")
        
except Exception as e:
    print(f"✗ Supabase connection failed: {e}")
    print("USE_SUPABASE would be: False")
