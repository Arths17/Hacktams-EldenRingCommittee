# CampusFuel - Vercel Deployment Guide

## 📋 Prerequisites
- GitHub account with your repository pushed
- Vercel account (sign up at vercel.com)
- Supabase project (supabase.com)

## 🚀 Deployment Steps

### 1. Prepare Your Repository

Push all changes to GitHub:
```bash
git add .
git commit -m "Add Vercel deployment configuration"
git push origin main
```

### 2. Import Project to Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Click "Import Git Repository"
3. Select your GitHub repository: `Arths17/Hacktams-EldenRingCommittee`
4. Click "Import"

### 3. Configure Build Settings

Vercel should auto-detect Next.js. Verify these settings:

- **Framework Preset**: Next.js
- **Root Directory**: `./` (leave blank)
- **Build Command**: `npm run build`
- **Output Directory**: `.next`
- **Install Command**: `npm install`

### 4. Configure Environment Variables

Click "Environment Variables" and add these:

#### Required Variables:
```
SECRET_KEY=your_secure_secret_key_here_min_32_chars
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
```

#### Optional Variables:
```
FRONTEND_URL=https://your-custom-domain.com
OLLAMA_URL=https://your-ollama-instance.com
```

**Where to find Supabase credentials:**
1. Go to your Supabase project dashboard
2. Click "Settings" → "API"
3. Copy "Project URL" for `SUPABASE_URL`
4. Copy "anon/public" key for `SUPABASE_KEY`

**Generate a secure SECRET_KEY:**
```bash
# Option 1: Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Option 2: Using OpenSSL
openssl rand -base64 32
```

### 5. Deploy

1. Click "Deploy"
2. Wait for build to complete (2-3 minutes)
3. Your site will be live at: `https://your-project.vercel.app`

### 6. Set Up Custom Domain (Optional)

1. Go to your project settings in Vercel
2. Click "Domains"
3. Add your custom domain
4. Update your DNS records as instructed
5. Add your domain to `FRONTEND_URL` environment variable

### 7. Verify Deployment

Test these endpoints:
- Frontend: `https://your-project.vercel.app`
- Health Check: `https://your-project.vercel.app/api/health`
- API Docs: `https://your-project.vercel.app/api/docs`

## 🔧 Configuration Files Created

- ✅ **vercel.json** - Routing configuration for Next.js + Python API
- ✅ **.vercelignore** - Files to exclude from deployment
- ✅ **.env.example** - Template for environment variables
- ✅ **next.config.mjs** - Updated for production/dev environments

## 🐛 Troubleshooting

### Build Fails
- Check Vercel build logs for errors
- Verify all dependencies are in package.json
- Ensure Python version is compatible (3.9+)

### API Routes Not Working
- Verify `vercel.json` routing is correct
- Check environment variables are set
- Review function logs in Vercel dashboard

### CORS Errors
- Verify your deployment URL is in CORS origins
- Check browser console for specific errors
- Ensure credentials are being sent correctly

### Database Connection Issues
- Verify Supabase credentials are correct
- Check Supabase project is not paused
- Review API logs for connection errors

## 📝 Post-Deployment

1. **Test all features**:
   - Login/Signup
   - Profile creation
   - AI chat
   - Meal logging

2. **Monitor**:
   - Check Vercel Analytics
   - Review function logs
   - Monitor Supabase usage

3. **Update endpoints**:
   - Update any hardcoded localhost URLs
   - Test API integrations

## 🔄 Redeploying

Vercel automatically redeploys when you push to main:
```bash
git add .
git commit -m "Your changes"
git push origin main
```

Manual redeploy:
1. Go to Vercel dashboard
2. Select your project
3. Click "Redeploy"

## 🔒 Security Checklist

- ✅ SECRET_KEY is strong and unique
- ✅ .env files are in .gitignore
- ✅ Supabase RLS policies are configured
- ✅ API rate limiting is enabled
- ✅ CORS is properly configured

## 📧 Support

If you encounter issues:
1. Check Vercel build logs
2. Review Vercel function logs
3. Check Supabase logs
4. Review this guide for common issues

## 🎉 You're Live!

Your CampusFuel app is now deployed and accessible worldwide!
