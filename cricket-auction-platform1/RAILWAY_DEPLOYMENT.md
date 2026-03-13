# Railway Deployment Guide - SKIT Premier League

## ✅ Fixed: Port Configuration Error

The deployment error has been fixed:
1. Added `gunicorn>=21.2.0` to `requirements.txt`
2. Fixed PORT environment variable handling in Procfile and railway.json
3. Updated main_new.py to read PORT from environment

## Next Steps:

### 1. Push Changes to GitHub
```bash
git add requirements.txt Procfile railway.json main_new.py
git commit -m "Fix Railway deployment - add gunicorn and PORT handling"
git push
```

Railway will automatically detect the changes and redeploy.

### 2. Set Environment Variables in Railway

Go to your Railway project → Variables tab and add:

**Required Variables:**
```
ENVIRONMENT=production
DEBUG=false
JWT_SECRET=<generate-random-256-bit-secret>
MONGODB_URL=<your-mongodb-atlas-connection-string>
```

**Optional but Recommended:**
```
REDIS_URL=<railway-redis-url-if-using>
CORS_ORIGINS=https://your-app.railway.app
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
```

### 3. MongoDB Atlas Setup (Free Tier)

1. Go to https://www.mongodb.com/cloud/atlas
2. Create free account
3. Create free M0 cluster (512MB)
4. Create database user
5. Whitelist all IPs: `0.0.0.0/0` (for Railway)
6. Get connection string:
   ```
   mongodb+srv://username:password@cluster.mongodb.net/cricket_auction?retryWrites=true&w=majority
   ```
7. Add this to Railway's `MONGODB_URL` variable

### 4. Generate JWT Secret

Run this command locally:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and set it as `JWT_SECRET` in Railway.

### 5. Create Admin User

After deployment succeeds:

1. Open Railway logs to see your app URL
2. SSH into Railway or use local script with production MongoDB URL:
   ```bash
   # Update MONGODB_URL in .env to point to Atlas
   python create_admin.py
   ```

Or create admin via MongoDB Atlas UI:
- Database: `cricket_auction`
- Collection: `users`
- Insert document:
```json
{
  "email": "admin@cricket.com",
  "password": "$2b$12$...", 
  "role": "admin",
  "is_active": true,
  "created_at": {"$date": "2026-02-16T00:00:00Z"}
}
```

### 6. Access Your Deployed App

Your app will be available at: `https://your-project-name.railway.app`

Login with: `admin@cricket.com` / `admin123`

## Troubleshooting

**If deployment still fails:**
1. Check Railway logs for errors
2. Verify all environment variables are set
3. Ensure MongoDB Atlas allows Railway IPs (0.0.0.0/0)
4. Check that PORT variable is not set (Railway sets it automatically)

**If app crashes on startup:**
- Check MongoDB connection string is correct
- Verify JWT_SECRET is set
- Check Railway logs: `railway logs`

## Cost Estimate

- Railway: $5/month (500 hours free trial)
- MongoDB Atlas: FREE (M0 tier - 512MB)
- Total: FREE for first month, then $5/month

## Railway Free Trial

Railway gives you $5 credit which equals ~500 hours of runtime. Perfect for testing!

---

**Status**: Ready to deploy! Just push the changes and set environment variables.
