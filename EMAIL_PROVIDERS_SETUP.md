# Email Providers Setup Guide

This guide covers all four email providers supported by the AI Lead Generation Tool. All providers work on any deployment platform (Replit, AWS, DigitalOcean, your own server, etc.).

---

## 📧 **Available Email Providers**

1. **Gmail OAuth** - Send from Gmail accounts using OAuth 2.0
2. **Outlook OAuth** - Send from Outlook/Microsoft accounts using OAuth 2.0
3. **SMTP** - Send from any email provider with SMTP support
4. **SendGrid** - Send via SendGrid API (no email account needed)

**All providers:**
- ✅ Work on any deployment platform
- ✅ Per-user configuration (each user sets up their own)
- ✅ Encrypted credential storage
- ✅ No Replit-specific dependencies

---

## 1️⃣ Gmail OAuth Setup

**Best for:** Users with Gmail or Google Workspace accounts

### Developer Setup (One-time):

See **`GMAIL_OAUTH_SETUP.md`** for detailed instructions. Quick summary:

1. Create Google Cloud project
2. Enable Gmail API
3. Configure OAuth consent screen
4. Create OAuth credentials
5. Add three secrets:
   ```
   GOOGLE_OAUTH_CLIENT_ID=your-client-id
   GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
   GOOGLE_OAUTH_REDIRECT_URI=https://yourdomain.com/api/email/auth/gmail/callback
   ```

### User Setup:
1. Go to Settings → Select "Gmail"
2. Click "Connect Gmail"
3. Sign in with Google account
4. Grant email sending permissions
5. ✅ Done!

---

## 2️⃣ Outlook OAuth Setup

**Best for:** Users with Outlook.com, Hotmail, or Microsoft 365 accounts

### Developer Setup (One-time):

1. **Go to** [Azure Portal](https://portal.azure.com/)
2. **Navigate to** "Azure Active Directory" → "App registrations"
3. **Click** "New registration"
4. **Fill in:**
   - Name: AI Lead Gen Tool
   - Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
   - Redirect URI: Web → `https://yourdomain.com/api/email/auth/outlook/callback`
5. **Click** "Register"
6. **Copy Application (client) ID**
7. **Create Client Secret:**
   - Go to "Certificates & secrets"
   - Click "New client secret"
   - Add description, set expiration
   - Copy the secret value (shown only once!)
8. **Set API Permissions:**
   - Go to "API permissions"
   - Click "Add a permission" → "Microsoft Graph"
   - Select "Delegated permissions"
   - Add: `Mail.Send`, `User.Read`, `offline_access`
   - Click "Add permissions"
   - Click "Grant admin consent" (if available)
9. **Add secrets to your app:**
   ```
   MS_CLIENT_ID=your-application-client-id
   MS_CLIENT_SECRET=your-client-secret-value
   MS_REDIRECT_URI=https://yourdomain.com/api/email/auth/outlook/callback
   ```

### User Setup:
1. Go to Settings → Select "Outlook"
2. Click "Connect Outlook"
3. Sign in with Microsoft account
4. Grant email sending permissions
5. ✅ Done!

### Notes:
- Works with Outlook.com, Hotmail.com, and Microsoft 365
- Tokens automatically refresh
- Each user sends from their own Microsoft account

---

## 3️⃣ SMTP Setup

**Best for:** Users with any email provider (Gmail, Outlook, Zoho, Office 365, custom servers, etc.)

### No Developer Setup Required!

Each user configures their own SMTP server directly in the app.

### User Setup:

1. **Get SMTP credentials from your email provider:**

   **Gmail:**
   - Enable 2-factor authentication
   - Generate App Password at [Google Account](https://myaccount.google.com/apppasswords)
   - SMTP: `smtp.gmail.com`, Port: `587`, TLS: Yes

   **Outlook/Hotmail:**
   - SMTP: `smtp-mail.outlook.com`, Port: `587`, TLS: Yes
   - Use your regular email password

   **Office 365:**
   - SMTP: `smtp.office365.com`, Port: `587`, TLS: Yes
   - Use your work email password

   **Zoho Mail:**
   - SMTP: `smtp.zoho.com`, Port: `587`, TLS: Yes

   **Custom Server:**
   - Contact your email provider for SMTP settings

2. **In the app:**
   - Go to Settings → Select "SMTP"
   - Enter SMTP host (e.g., `smtp.gmail.com`)
   - Enter SMTP port (usually `587` for TLS or `465` for SSL)
   - Enter username (usually your email address)
   - Enter password (use App Password for Gmail)
   - Enter "From" email address
   - Enable TLS (recommended)
   - Click "Save SMTP Settings"
3. ✅ Done!

### Security Notes:
- Password encrypted at rest using Fernet
- Use App Passwords for Gmail (never your real password)
- TLS encryption for secure transmission

---

## 4️⃣ SendGrid Setup

**Best for:** High-volume sending, users without email accounts, transactional emails

### No Developer Setup Required!

Each user gets their own SendGrid API key.

### User Setup:

1. **Create SendGrid account:**
   - Go to [SendGrid.com](https://sendgrid.com/)
   - Sign up (free tier: 100 emails/day)
   
2. **Create API Key:**
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Name: "AI Lead Gen Tool"
   - Permissions: "Full Access" or "Mail Send" (restricted)
   - Copy the API key (shown only once!)

3. **Verify sender email:**
   - Go to Settings → Sender Authentication
   - Click "Verify a Single Sender"
   - Enter your email and details
   - Check email and click verification link

4. **In the app:**
   - Go to Settings (main settings, not email provider settings)
   - Scroll to "API Keys" section
   - Enter SendGrid API Key
   - Enter "From Email" (the verified email from step 3)
   - Click "Save API Keys"
   - Go back to Settings → Email Provider
   - Select "SendGrid"
5. ✅ Done!

### Benefits:
- No email account required (just API key)
- High deliverability
- Detailed analytics
- Free tier available (100 emails/day)
- Scales to millions of emails

### Pricing:
- **Free:** 100 emails/day forever
- **Essentials:** $19.95/month (50,000 emails/month)
- **Pro:** Custom pricing

---

## 📊 **Comparison Table**

| Provider | Setup Difficulty | Best For | Rate Limits | Cost |
|----------|-----------------|----------|-------------|------|
| **Gmail OAuth** | Medium (dev setup) | Personal Gmail users | 500/day (free), 2000/day (workspace) | Free / $6/user/month |
| **Outlook OAuth** | Medium (dev setup) | Microsoft account users | 300/day (free), 10,000/day (365) | Free / $6/user/month |
| **SMTP** | Easy (no dev setup) | Any email provider | Varies by provider | Depends on provider |
| **SendGrid** | Easy (no dev setup) | High-volume, transactional | 100/day (free), 50K/month (paid) | Free - $19.95/month |

---

## 🔒 **Security Best Practices**

### For All Providers:
- ✅ All credentials encrypted at rest (Fernet)
- ✅ Per-user credential storage (no sharing)
- ✅ HTTPS required for OAuth flows
- ✅ Automatic token refresh for OAuth

### Recommendations:
1. **Gmail/Outlook:** Use OAuth (more secure than SMTP passwords)
2. **SMTP Gmail:** Always use App Passwords, never real password
3. **Production:** Use environment variables for OAuth secrets
4. **Never commit** secrets to git (use `.env`, `.gitignore`)

---

## 🚀 **Production Deployment Checklist**

### Before Deploying:

**For Gmail OAuth:**
- [ ] Google Cloud project created
- [ ] Gmail API enabled
- [ ] OAuth consent screen configured
- [ ] Redirect URI updated to production domain
- [ ] Secrets added to production environment

**For Outlook OAuth:**
- [ ] Azure app registration created
- [ ] API permissions granted
- [ ] Redirect URI updated to production domain
- [ ] Secrets added to production environment

**For SMTP:**
- [ ] No special setup (users configure directly)

**For SendGrid:**
- [ ] No special setup (users configure directly)

### Environment Variables (Production):

```bash
# Gmail OAuth (if using)
GOOGLE_OAUTH_CLIENT_ID=your-production-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-production-client-secret
GOOGLE_OAUTH_REDIRECT_URI=https://yourdomain.com/api/email/auth/gmail/callback

# Outlook OAuth (if using)
MS_CLIENT_ID=your-production-client-id
MS_CLIENT_SECRET=your-production-client-secret
MS_REDIRECT_URI=https://yourdomain.com/api/email/auth/outlook/callback

# No environment variables needed for SMTP or SendGrid!
# Users configure these directly in the app.
```

---

## 🐛 **Troubleshooting**

### Gmail OAuth:
- **"redirect_uri_mismatch"** → Check redirect URI in Google Console matches your secret exactly
- **"insufficient permissions"** → Add `gmail.send` scope in OAuth consent screen
- **"App not verified"** → Normal for testing, click "Advanced" to proceed

### Outlook OAuth:
- **"AADSTS50011: redirect URI mismatch"** → Check Azure redirect URI matches your secret
- **"insufficient privileges"** → Make sure `Mail.Send` permission is granted
- **"Token expired"** → Automatic refresh should handle this, check logs

### SMTP:
- **"Authentication failed"** → For Gmail, use App Password not real password
- **"Connection refused"** → Check SMTP host and port are correct
- **"TLS error"** → Try enabling/disabling TLS, use port 465 for SSL

### SendGrid:
- **"Unauthorized"** → Check API key is correct and not expired
- **"Sender not verified"** → Verify sender email in SendGrid dashboard
- **"Daily limit exceeded"** → Upgrade SendGrid plan or wait 24 hours

---

## 💡 **Recommendations**

### For Small Teams (1-10 users):
→ **SMTP** (easiest setup, no developer work)

### For Personal Use:
→ **Gmail OAuth** or **Outlook OAuth** (if using those email providers)

### For High-Volume Sending:
→ **SendGrid** (best deliverability, detailed analytics)

### For Mixed Team:
→ **Support all 4** (let users choose what works for them)

---

## 📞 **Support Resources**

- **Gmail API:** [Google API Console](https://console.cloud.google.com/)
- **Outlook API:** [Azure Portal](https://portal.azure.com/)
- **SendGrid:** [SendGrid Docs](https://docs.sendgrid.com/)
- **SMTP Settings:** Check your email provider's support docs

---

**All email providers are production-ready and work on any deployment platform!** 🚀
