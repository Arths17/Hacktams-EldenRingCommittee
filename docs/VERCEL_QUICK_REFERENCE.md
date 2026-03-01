# Vercel Deployment Quick Reference

## 🎯 Essential Info for Vercel Setup

### Framework Settings
```
Framework: Next.js
Build Command: npm run build
Output Directory: .next
Install Command: npm install
Root Directory: ./
Node Version: 18.x (or latest LTS)
```

### Environment Variables (Add in Vercel Dashboard)

#### 1. SECRET_KEY
```
Name: SECRET_KEY
Value: [Generate using: python -c "import secrets; print(secrets.token_urlsafe(32))"]
```

#### 2. SUPABASE_URL
```
Name: SUPABASE_URL
Value: https://[your-project-id].supabase.co
Location: Supabase Dashboard → Settings → API → Project URL
```

#### 3. SUPABASE_KEY
```
Name: SUPABASE_KEY
Value: [Your anon/public key]
Location: Supabase Dashboard → Settings → API → anon public key
```

### Quick Commands

Generate SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Push to deploy:
```bash
git add .
git commit -m "Deploy to Vercel"
git push origin main
```

Test locally before deploy:
```bash
npm run build
npm start
```

### Vercel Project URL Pattern
```
https://[project-name]-[team-name].vercel.app
or
https://[project-name].vercel.app
```

### Test These After Deployment
- ✅ Homepage: https://your-app.vercel.app
- ✅ Health: https://your-app.vercel.app/api/health
- ✅ API Docs: https://your-app.vercel.app/api/docs
- ✅ Login: https://your-app.vercel.app/login
- ✅ Dashboard: https://your-app.vercel.app/dashboard

### Common Issues & Fixes

**Build fails:**
- Check package.json has all dependencies
- Verify Node.js version compatibility
- Review build logs in Vercel

**API not working:**
- Verify environment variables are set
- Check vercel.json routing
- Review function logs

**CORS errors:**
- Deployment URL is auto-allowed
- Custom domains need FRONTEND_URL env var

**Database errors:**
- Double-check Supabase credentials
- Verify Supabase project is active
- Check RLS policies if enabled

### Files Created for Deployment
- ✅ vercel.json - Routing configuration
- ✅ .vercelignore - Exclude files
- ✅ .env.example - Template
- ✅ VERCEL_DEPLOYMENT.md - Full guide

### Support
- Vercel Docs: https://vercel.com/docs
- Vercel Discord: https://vercel.com/discord
- Supabase Docs: https://supabase.com/docs
