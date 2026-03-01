import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

# List all users in Supabase
result = sb.table("users").select("id, username, created_at").execute()

print(f"Total users in Supabase: {len(result.data)}")
print("\nUsers:")
for user in result.data:
    print(f"  - ID: {user.get('id')}, Username: {user.get('username')}, Created: {user.get('created_at', 'N/A')}")
