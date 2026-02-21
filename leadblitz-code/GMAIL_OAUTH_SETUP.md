# Gmail OAuth Setup Guide

This guide explains how to set up Gmail OAuth for your AI Lead Generation Tool so that your users can send emails from their own Gmail accounts.

## Overview

- **You (developer)** set up ONE Google OAuth app and add credentials as secrets
- **Each user** of your app authenticates with their own Gmail account
- **Works anywhere** - Replit, AWS, DigitalOcean, your own server, etc.
- **Multi-tenant** - Each user sends from their own Gmail, tokens stored per-user in database

---

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name (e.g., "AI Lead Gen Tool")
4. Click "Create"

---

## Step 2: Enable Gmail API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Gmail API"
3. Click on it and press "Enable"

---

## Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select **"External"** user type → Click "Create"
3. Fill in the required fields:
   - **App name**: AI Lead Gen Tool (or your app name)
   - **User support email**: Your email address
   - **Developer contact**: Your email address
4. Click "Save and Continue"
5. **Scopes** page:
   - Click "Add or Remove Scopes"
   - Search for and add:
     - `https://www.googleapis.com/auth/gmail.send`
     - `https://www.googleapis.com/auth/userinfo.email`
   - Click "Update" → "Save and Continue"
6. **Test users** page:
   - Click "Add Users"
   - Add email addresses of users who will test the app
   - Click "Save and Continue"
7. Review and click "Back to Dashboard"

**Important:** Your app will be in "Testing" mode, which limits it to 100 test users. To remove this limit, you need to verify your app (requires domain ownership) or keep it in testing mode for internal use.

---

## Step 4: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Select **"Web application"**
4. Enter name: "AI Lead Gen Web Client"
5. **Authorized redirect URIs**:
   - For **Replit development**: `https://YOUR-REPL-NAME.YOUR-USERNAME.repl.co/api/email/auth/gmail/callback`
   - For **production deployment**: `https://yourdomain.com/api/email/auth/gmail/callback`
   - You can add multiple redirect URIs for different environments
6. Click "Create"
7. **Copy your credentials**:
   - **Client ID**: Starts with something like `123456789-abc...apps.googleusercontent.com`
   - **Client Secret**: A random string like `GOCSPX-...`

---

## Step 5: Add Secrets to Your Application

### On Replit:
1. Click "Tools" → "Secrets" (lock icon in sidebar)
2. Add these three secrets:

```
GOOGLE_OAUTH_CLIENT_ID = your-client-id-here
GOOGLE_OAUTH_CLIENT_SECRET = your-client-secret-here
GOOGLE_OAUTH_REDIRECT_URI = https://YOUR-REPL.repl.co/api/email/auth/gmail/callback
```

### On Production Server (Environment Variables):
```bash
export GOOGLE_OAUTH_CLIENT_ID="your-client-id-here"
export GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret-here"
export GOOGLE_OAUTH_REDIRECT_URI="https://yourdomain.com/api/email/auth/gmail/callback"
```

Or add to your `.env` file (never commit this to git!):
```
GOOGLE_OAUTH_CLIENT_ID=your-client-id-here
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret-here
GOOGLE_OAUTH_REDIRECT_URI=https://yourdomain.com/api/email/auth/gmail/callback
```

---

## Step 6: Test Gmail Connection

1. **Login** to your app
2. Go to **Settings**
3. Click **Gmail** provider card
4. Click **"Connect Gmail"** button
5. A popup window opens → Sign in with your Google account
6. Grant permissions to send emails
7. Window closes → You should see "Gmail successfully connected"

---

## How It Works

### For Each User:

1. User clicks "Connect Gmail" in Settings
2. OAuth popup opens → User signs in with their Gmail
3. Google redirects back with authorization code
4. Backend exchanges code for access token + refresh token
5. Tokens are encrypted and stored in database (per-user)
6. When sending email:
   - System retrieves user's encrypted tokens
   - If expired, automatically refreshes using refresh token
   - Sends email via Gmail API from user's account

### Security:

- ✅ **Encrypted tokens**: All OAuth tokens encrypted at rest using Fernet
- ✅ **Per-user isolation**: Each user's tokens stored separately in database
- ✅ **Automatic refresh**: Expired tokens refreshed automatically
- ✅ **Secure OAuth**: Standard OAuth 2.0 flow, no passwords stored
- ✅ **HTTPS only**: OAuth requires HTTPS (works on Replit automatically)

---

## Troubleshooting

### "Gmail OAuth not configured" error
→ Make sure you've added all three secrets: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`

### "redirect_uri_mismatch" error
→ The redirect URI in your Google Cloud Console must EXACTLY match your secret. Check for:
- Extra/missing `/` at the end
- `http` vs `https`
- Correct domain/Repl URL

### "Access blocked: This app's request is invalid"
→ You forgot to add the Gmail API scopes in the OAuth consent screen (Step 3)

### "This app is not verified" warning
→ Normal for testing. Click "Advanced" → "Go to [Your App] (unsafe)" to proceed. For production, you need to verify your app with Google.

### User gets "insufficient permissions" when sending
→ Make sure you added `https://www.googleapis.com/auth/gmail.send` scope

---

## Production Deployment

When deploying to production:

1. **Update redirect URI** in Google Cloud Console to your production domain
2. **Add production URI** to Secrets/Environment Variables
3. **Consider app verification** if you'll have >100 users (requires domain ownership)
4. **Use HTTPS** - OAuth requires secure connection
5. **Keep secrets secure** - Never commit to git, use environment variables

---

## Multi-Environment Setup

You can have different OAuth apps for dev/staging/production:

**Development (Replit):**
```
GOOGLE_OAUTH_CLIENT_ID = dev-client-id
GOOGLE_OAUTH_REDIRECT_URI = https://dev-repl.repl.co/api/email/auth/gmail/callback
```

**Production:**
```
GOOGLE_OAUTH_CLIENT_ID = prod-client-id
GOOGLE_OAUTH_REDIRECT_URI = https://yourdomain.com/api/email/auth/gmail/callback
```

Or use the same OAuth app with multiple redirect URIs (recommended for simplicity).

---

## Support

If you encounter issues:
1. Check Google Cloud Console → "APIs & Services" → "Credentials" for correct redirect URIs
2. Verify all three secrets are set correctly
3. Check browser console for error messages
4. Ensure Gmail API is enabled in your Google Cloud project
5. Check your OAuth consent screen has the correct scopes

---

**That's it!** Your users can now connect their Gmail accounts and send emails directly from the app, no matter where it's deployed.
