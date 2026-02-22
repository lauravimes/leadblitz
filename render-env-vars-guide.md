# Render Environment Variables Setup Guide

## Critical Variables That Must Be Set

Go to your **Render service settings** → **Environment** tab and add these:

### **Required (App will fail without these):**

1. **DATABASE_URL**
   ```
   postgresql://username:password@hostname:5432/database_name
   ```
   - Get this from your PostgreSQL database provider (Render, Neon, etc.)

2. **OPENAI_API_KEY**
   ```
   sk-...your-openai-api-key...
   ```
   - Get from: https://platform.openai.com/api-keys

3. **ENCRYPTION_KEY** 
   ```
   your-32-character-encryption-key-here
   ```
   - Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

4. **SESSION_SECRET**
   ```
   your-random-session-secret-string
   ```
   - Any random string, like: `your-super-secret-session-key-2026`

### **Optional (Have defaults in render.yaml):**
- `BASE_URL` - Already set to your Render URL
- `CALENDLY_LINK` - Already set
- `FROM_EMAIL` - Already set

### **Nice to Have (App works without these):**
- `GOOGLE_MAPS_API_KEY` - For enhanced business search
- `STRIPE_PUBLISHABLE_KEY` + `STRIPE_SECRET_KEY` - For payments
- `GA_MEASUREMENT_ID` - For analytics

## How to Set in Render:

1. Go to **render.com dashboard**
2. Click your **leadblitz service** 
3. Go to **Settings** → **Environment**
4. Click **Add Environment Variable**
5. Add each key-value pair above

## Most Likely Issue:

Missing `DATABASE_URL` - Without this, the app crashes immediately on startup.

The debug script will show exactly which variables are missing!