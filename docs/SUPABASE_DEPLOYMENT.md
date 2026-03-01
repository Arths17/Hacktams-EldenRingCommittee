# HealthOS AI - Supabase Deployment Guide

## Overview

Your HealthOS AI backend is ready to deploy to Supabase. This guide walks you through the steps.

## ✅ Prerequisites

- [ ] Supabase project created: https://nqhtdyhyuczdpudnaiuu.supabase.co
- [ ] SUPABASE_URL in .env ✓
- [ ] SUPABASE_KEY in .env ✓

## 📋 Step-by-Step Deployment

### Step 1: Deploy Database Schema

1. Open your Supabase Dashboard:
   - URL: https://app.supabase.com
   - Select project: **nqhtdyhyuczdpudnaiuu**

2. Go to **SQL Editor** (left sidebar)

3. Click **"New query"** button

4. Copy entire contents from `docs/database_schema.sql`

5. Paste into SQL editor

6. Click **"Run"** button

**Expected Result**: No errors, schema deployed successfully

---

### Step 2: Verify Schema Deployment

In Supabase dashboard:

1. Go to **Table Editor** (left sidebar)
2. You should see these tables:
   - users
   - health_profiles
   - health_metrics
   - meals
   - meal_logs
   - health_goals
   - workouts
   - feedback
   - user_events
   - experiments
   - experiment_variants
   - variant_assignments
   - experiment_results
   - user_segments
   - churn_features
   - churn_interventions
   - recommendation_cache
   - system_logs

3. Click on **meals** table → should see 3 sample meals loaded

---

### Step 3: Configure Authentication

1. Go to **Authentication** (left sidebar)

2. Click **"Providers"**

3. Enable **Email/Password**:
   - Toggle ON
   - Enable **"Autoconfirm email"** (for development)
   - Click **"Save"**

4. Go to **URL Configuration** (in Authentication):
   - Add these redirect URLs:
     - `http://localhost:3000`
     - `http://localhost:8000`
     - `http://127.0.0.1:3000`
   - Click **"Save"**

5. Go to **JWT Secret** (in Authentication):
   - Copy the JWT Secret value
   - Add to your `.env` file:
     ```
     JWT_SECRET=<paste_value_here>
     ```

---

### Step 4: Get API Keys

1. Go to **Project Settings** (left sidebar, gear icon)

2. Click **"API"**

3. Copy these values:
   - **Anon key** → Already in `.env` as `SUPABASE_KEY` ✓
   - **Service Role key** → Add to `.env`:
     ```
     SERVICE_ROLE_KEY=<paste_value_here>
     ```

4. Update your `.env` file and save

---

### Step 5: Test Connection

Run the connection test:

```bash
cd "/Users/atharvranjan/Hacktams-EldenRingCommittee "
python test_supabase_connection.py
```

**Expected Output**:
```
✓ Connection successful!
✓ Users table exists
✓ Health profiles table exists
✓ Meals table exists (3 sample meals)
✓ ALL TESTS PASSED
```

---

### Step 6: Verify RLS Policies

1. Go to **Authentication** → **Policies**

2. For each table, you should see policies:
   - `users`: "Users can view own profile", "Users can update own profile"
   - `health_profiles`: View and update policies
   - `health_metrics`: View and insert policies
   - `meal_logs`: View and insert policies

**Note**: RLS policies are enabled but may need refinement based on your auth implementation.

---

## 🔄 Row-Level Security (RLS)

The schema includes basic RLS policies. For production:

1. **Fine-tune policies** based on your auth implementation
2. **Test policies** with different user roles
3. **Review security** with Supabase docs

Key policies enforced:
- Users can only see their own health data
- Users can only see their own meal logs
- Users can only see their own events
- Admin users (future) can see all data

---

## 🧪 Test Your Setup

### 1. Test Database Connection

```bash
python test_supabase_connection.py
```

### 2. Test Churn Prediction Module

```bash
python test_churn_simple.py
```

### 3. Test API Endpoints

```bash
# Start the server
uvicorn main:app --reload

# In another terminal
curl http://localhost:8000/health
curl http://localhost:8000/api/docs
```

---

## 📊 Database Structure

### Core Tables

| Table | Purpose | Rows | Indexes |
|-------|---------|------|---------|
| **users** | User accounts | ~100s | email, created_at, is_active |
| **health_profiles** | User health info | ~100s | user_id, updated_at |
| **health_metrics** | Time-series health data | ~1000s | user_id_date, user_id |
| **meals** | Meal catalog | ~100s | created_at, tags (GIN) |
| **meal_logs** | User meal tracking | ~1000s | user_id_date, user_id |

### Analytics Tables

| Table | Purpose |
|-------|---------|
| **user_events** | Event logging for analytics |
| **experiments** | A/B test configuration |
| **experiment_variants** | Test variants |
| **variant_assignments** | User-variant mapping |
| **experiment_results** | Experiment metrics |

### Churn Prediction Tables

| Table | Purpose |
|-------|---------|
| **churn_features** | Pre-calculated churn features |
| **churn_interventions** | At-risk user interventions |
| **user_segments** | User clustering |

---

## ⚠️ Common Issues

### Issue: "Table already exists" error

**Solution**: Tables already created. Run schema once per project.

### Issue: Connection test fails

**Solution**: 
1. Verify SUPABASE_URL and SUPABASE_KEY in `.env`
2. Check Supabase status: https://status.supabase.com
3. Ensure project is active (not paused)

### Issue: RLS policy errors

**Solution**:
1. Check auth configuration
2. Verify JWT Secret is set
3. Update policies in Supabase UI as needed

---

## 🚀 Next Steps

After successful deployment:

1. **Start the API server**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Test all endpoints**:
   - Visit: http://localhost:8000/api/docs
   - Try signup/login endpoints
   - Test chat endpoint
   - Test churn prediction

3. **Build frontend** (Next.js):
   - Create React components
   - Connect to API
   - Implement auth flow

4. **Deploy to production**:
   - Set up CD/CI pipeline
   - Configure production secrets
   - Deploy API to cloud
   - Deploy frontend

---

## 📚 Resources

- Supabase Docs: https://supabase.com/docs
- Database Docs: https://supabase.com/docs/guides/database
- RLS Guide: https://supabase.com/docs/learn/auth-deep-dive/row-level-security
- Auth Guide: https://supabase.com/docs/guides/auth

---

## ✅ Deployment Checklist

- [ ] Schema deployed to Supabase
- [ ] Tables verified in Table Editor
- [ ] Sample meals loaded (3 meals)
- [ ] Authentication configured
- [ ] JWT Secret set
- [ ] API keys configured
- [ ] RLS policies verified
- [ ] Connection test passed
- [ ] API server starts successfully
- [ ] Endpoints respond correctly

---

**Status**: Ready for deployment! 🎉

Last updated: March 1, 2026
