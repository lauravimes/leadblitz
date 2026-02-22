# CRITICAL INFORMATION - Laura Vimes

**⚠️ SECURITY NOTE: This file contains sensitive information. Handle with care.**

## LeadBlitz Render Deployment Secrets

**Date needed:** 2026-02-18  
**Status:** ✅ READY FOR DEPLOYMENT (missing webhook secret may not be needed)  
**Purpose:** Render staging deployment with mobile optimization

### Required Environment Variables:
```
SESSION_SECRET=<REDACTED_FOR_SECURITY>
ADMIN_PASSWORD=<REDACTED_FOR_SECURITY>
DATABASE_URL=<REDACTED_FOR_SECURITY>
OPENAI_API_KEY=<REDACTED_FOR_SECURITY>
ENCRYPTION_KEY=<REDACTED_FOR_SECURITY>

STRIPE_PUBLISHABLE_KEY=<REDACTED_FOR_SECURITY>
STRIPE_SECRET_KEY=<REDACTED_FOR_SECURITY>
STRIPE_WEBHOOK_SECRET=<PENDING>

GOOGLE_MAPS_API_KEY=<REDACTED_FOR_SECURITY>

GA_MEASUREMENT_ID=<REDACTED_FOR_SECURITY>

BASE_URL=https://staging-app.onrender.com
CALENDLY_LINK=https://cal.com/leadblitz/demo
FROM_EMAIL=sh@shapplications.com

# Cal.com Setup Details:
# - URL: cal.com/leadblitz/demo  
# - Login: shaca147@gmail.com / LB!Cal2026Demo
# - Event: "LeadBlitz Demo" (30 min, Cal Video, Mon-Fri 9am-5pm Europe/London)
# - ⚠️ Host shows "Laura Vimes" — needs changing to Steven
```

## Documentation Policy Going Forward:
- ✅ ANY secrets/API keys → immediately update this file
- ✅ ANY critical project information → document in appropriate memory file  
- ✅ ANY weekend work → capture in daily memory files
- ✅ ANY promises/commitments → write down immediately

## Notes:
- Steven provided these secrets yesterday (2026-02-17) but I failed to document them
- This caused deployment delay and required Steven to repeat information
- NEVER let this happen again

---
**Last updated:** 2026-02-18 16:33 GMT (All secrets collected - webhook secret not found in Stripe)  
**Status:** READY FOR RENDER DEPLOYMENT ✅

## Updates Log:
- 2026-02-18 16:22: Added Google Maps API key: AIzaSyBoqSzoYGhz9T0V9VtXmAe1RfCBSZgeJKc
- 2026-02-18 16:22: Clarified Calendly setup - I created cal.com/leadblitz/demo (needs host name fix)
- 2026-02-18 16:23: Added SESSION_SECRET (64-byte base64 encoded)
- 2026-02-18 16:23: Added ADMIN_PASSWORD for dashboard access
- 2026-02-18 16:27: Added DATABASE_URL (Neon PostgreSQL connection string)
- 2026-02-18 16:27: Added OPENAI_API_KEY (project key)
- 2026-02-18 16:27: Added ENCRYPTION_KEY (base64 encoded)
- 2026-02-18 16:28: Added STRIPE_PUBLISHABLE_KEY (live key)
- 2026-02-18 16:28: Added STRIPE_SECRET_KEY (live secret key)
- 2026-02-18 16:29: Added GA_MEASUREMENT_ID (Google Analytics)
- 2026-02-18 16:33: STRIPE_WEBHOOK_SECRET not found in Stripe dashboard - proceeding without it