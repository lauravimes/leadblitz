# LeadBlitz Voice Receptionist — Full Spec
**Twilio Number:** 07427 916999
**Status:** Basic receptionist exists, post-call workflows missing

---

## Call Flow

### 1. Greeting
> "Hi, thanks for calling LeadBlitz! I'm our AI assistant. Are you calling about a **demo of LeadBlitz**, **support with your account**, or **something else**?"

### 2. Route Based on Intent

#### Path A: Demo / Sales
1. Collect caller's name and email
2. Brief 60-second elevator pitch:
   > "LeadBlitz helps web designers find clients using AI. You search for businesses, we score their websites, and generate professional audit reports you can send to prospects. It turns cold outreach into warm conversations."
3. Offer options:
   - "I can **email you a link to book a live demo** with our founder Steven"
   - "Or I can **add you to our waitlist** for early access"
4. **Post-call action:** Send email via SMTP with:
   - Calendar booking link (Calendly/Cal.com)
   - Brief LeadBlitz summary
   - Link to leadblitz.co

#### Path B: Support
1. Collect caller's name and email
2. Ask them to describe their issue
3. AI summarises the issue back to confirm
4. **Post-call action:** Send email via SMTP with:
   - "Thanks for calling LeadBlitz support"
   - Summary of the issue discussed
   - "We'll get back to you within 24 hours"
   - Also send internal notification to Steven (shaca147@gmail.com)

#### Path C: Other / General
1. Collect caller's name and email
2. Take a message
3. **Post-call action:** Send email via SMTP with:
   - "Thanks for calling LeadBlitz"
   - Summary of the conversation
   - "Someone will be in touch shortly"
   - Internal notification to Steven

---

## Technical Architecture

### Option 1: Twilio Studio + Functions (Recommended)
- **Twilio Studio** for the visual call flow (drag & drop)
- **Twilio Functions** for post-call webhooks
- **LeadBlitz API endpoint** `/api/twilio/post-call` to handle email sending

### Option 2: Pure TwiML + Webhooks
- TwiML for call routing
- Webhook to LeadBlitz FastAPI backend
- More code, more control, but harder to maintain

### Recommendation: Option 1 (Studio + Functions)
- Easier to iterate on the call flow
- Steven can tweak greetings/routing without code
- Functions handle the email logic

---

## Implementation Steps

### Step 1: Create Twilio Studio Flow
- Build the IVR with speech recognition
- Three branches: Demo, Support, Other
- Collect name + email via speech-to-text
- End call with appropriate goodbye message

### Step 2: Add Post-Call Webhook
- Twilio Function that fires when call ends
- Passes: caller_phone, caller_name, caller_email, call_type, call_summary
- Hits LeadBlitz API endpoint

### Step 3: LeadBlitz Backend Endpoint
Add to FastAPI app:
```
POST /api/twilio/post-call
{
  "caller_phone": "+447...",
  "caller_name": "John Smith",
  "caller_email": "john@example.com",
  "call_type": "demo|support|other",
  "call_summary": "AI-generated summary of the call"
}
```

This endpoint:
1. Sends branded email to caller (using existing system_email.py)
2. **Sends notification to Laura (laura.vimes@icloud.com)** — she triages all calls
3. Laura handles: follow-ups, demo scheduling, support resolution
4. Laura escalates to Steven (shaca147@gmail.com) only when needed
5. If demo request → caller gets calendar booking link, Laura gets notified to confirm
6. If support → Laura investigates/resolves or escalates
7. Optionally creates a lead in LeadBlitz CRM

### Call Triage Ownership
- **Laura (AI Chief of Staff)** is first responder for ALL calls
- Laura monitors laura.vimes@icloud.com for post-call notifications
- Laura sends follow-up responses, books demos, handles support
- Steven only gets pinged on Telegram for: demo bookings, urgent issues, or things Laura can't resolve

### Step 4: Calendar Booking
Options:
- **Calendly** (free tier, 1 event type) — fastest
- **Cal.com** (open source, free) — more control
- **Custom** — LeadBlitz booking page (most work)

Recommendation: Start with Calendly free tier. Steven creates a "LeadBlitz Demo" event type, we embed the link.

### Step 5: Email Templates

#### Demo Follow-up Email
```
Subject: Your LeadBlitz Demo Booking Link 🚀

Hi {name},

Thanks for calling LeadBlitz! As promised, here's your link to book a live demo:

👉 [Book Your Demo]({calendly_link})

In the meantime, check out what LeadBlitz can do: https://leadblitz.co

Looking forward to showing you how AI-powered lead generation 
can help you find more web design clients.

Best,
Steven Hallissey
Founder, LeadBlitz
```

#### Support Follow-up Email
```
Subject: LeadBlitz Support — Your Issue #{ticket_id}

Hi {name},

Thanks for calling LeadBlitz support. Here's a summary of what we discussed:

{call_summary}

We'll get back to you within 24 hours with an update. 
If it's urgent, reply to this email.

Best,
LeadBlitz Support Team
```

#### General Follow-up Email
```
Subject: Thanks for Calling LeadBlitz

Hi {name},

Thanks for reaching out to LeadBlitz. Here's a summary of your call:

{call_summary}

Someone will be in touch shortly. In the meantime, 
visit us at https://leadblitz.co

Best,
The LeadBlitz Team
```

---

## Replit Prompt (for building the backend endpoint)

See: `/leadblitz/replit-prompt-twilio-postcall.md`

---

## Dependencies
- [ ] Twilio Account SID + Auth Token
- [ ] Calendly (or Cal.com) booking link
- [ ] Twilio Studio flow created
- [ ] Twilio Function for post-call webhook
- [ ] LeadBlitz `/api/twilio/post-call` endpoint
- [ ] Email templates added to system_email.py

---

## Cost
- Twilio Studio: Free tier handles first 1,000 executions/month
- Twilio Functions: Included
- Calendly: Free tier (1 event type)
- Total additional cost: £0/month for MVP
