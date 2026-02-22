# MEMORY.md — Laura Vimes' Long-Term Memory
**Last updated:** 2026-02-19

## Who I Am
- Laura Vimes, AI Chief of Staff to Steven Hallissey
- Emoji: 🦎
- Email: laura.vimes@icloud.com (himalaya configured, iCloud IMAP/SMTP)
- Telegram: connected to Steven (user ID 7842991572)

## Who Steven Is
- Steven Hallissey, founder of SH Applications Limited
- Based in Woodley, Reading, Berkshire, UK (GMT timezone)
- Email: shaca147@gmail.com
- Mobile: +44 7967577037
- Family: Helena (partner), Charlotte (23, Wimbledon), William (19, Manchester Uni), Zachary (nearly 3, March 2026)
- Dev platform: Replit (no-code/low-code)
- LinkedIn: has personal account, no LeadBlitz company page yet

## The Business — SH Applications Limited

### DinoRoars (iOS App) — LIVE
- Dinosaur sounds & learning app for kids 4+
- Launched iOS App Store: 13 Jan 2026
- Apple ID: 6755724419, Bundle: com.shapps.dinoroars
- Free + $1.99 IAP to unlock all 18 dinos. No ads. No data collection.
- ~30 downloads, 7 purchases. Zero reviews.
- FB page: 60k+ video views, 200 followers pre-launch, then went quiet
- Web app: https://dinosaur-sounds-shaca147.replit.app
- Key issue: marketing, not product. ASO plan created.

### LeadBlitz (SaaS) — PRE-LAUNCH
- AI lead gen for web design solopreneurs
- Website: leadblitz.co (has good landing page)
- Search businesses → AI score websites → email/SMS outreach → CRM
- Credit-based: $15/$59/$199 per month
- Google Places + GPT-4o scoring + Hunter.io + Twilio
- One beta tester so far (loved it, got SMS results)
- Twilio number: 07427 916999 (basic voice receptionist)
- Key priority: test everything, fix bugs, recruit 10 Reddit ambassadors, FAST launch
- Competitors: Apollo.io (general B2B, 275M contacts, not direct threat), Jeeva.ai (AI sales agents, $95-560/mo), Cefer.io (300M contacts, cheap $19-29/mo)
- Strategic position: "Apollo is a firehose, LeadBlitz is a sniper rifle" — don't compete on data breadth, win on AI scoring + web design niche
- Data strategy: consider People Data Labs for decision-maker depth, but Google Places is right source for local biz
- 10 Reddit beta ambassadors planned (500 free credits each) — after app is bulletproof
- 10 Replit fix prompts sent to Steven (2 email batches)
- POSITIONING: "Find businesses with terrible websites, get them scored automatically, and reach out via personalized email or SMS — all from one dashboard"
- Unique angle: No other tool combines local business discovery + AI website quality scoring + built-in multi-channel outreach specifically for web designers
- LinkedIn strategy: Company page setup complete, daily posting automation, aim for thought leadership in web design niche
- Launch plan: Start with 10 Reddit ambassadors → validate product-market fit → scale marketing → premium feature rollout

### TotTrack (Child Dev Tracking) — DEVELOPMENT PHASE
- Target market: Parents of toddlers aged 1-4 (gap in market after baby tracking apps stop at 6 months)
- Key differentiator: SEND report generation for healthcare professionals (health visitors, GPs) — killer feature no competitor has
- 54 guided activities across 7 developmental areas with audio instructions  
- Built by Steven (father of Zachary) — authentic personal story behind product
- Positioning: "The only development tracking app purpose-built for toddlers aged 1–4"
- UK launch planned for 2026, strong potential in parenting app market

## Working Style & Preferences
- Steven hates "I can't do X but you could" — figure it out
- Be honest, frank, high-energy
- Send Replit fix prompts by email for bugs found
- Daily briefings: 6am and 6pm UK time (Telegram + email with project board)
- Steven thinks LeadBlitz has biggest revenue potential (I agree)
- US market is critical for DinoRoars
- **LeadBlitz monitoring:** Silent success, loud failures. Only Telegram Steven if something's broken, not if it's working fine

## Infrastructure
- Mac: Laura's MacBook Air, macOS Darwin 24.6.0, physically located at Steven's home in Woodley, Reading
- Chrome installed via homebrew, browser relay extension loaded
- himalaya email configured (iCloud, save-copy disabled due to IMAP mailbox issue)
- LeadBlitz account: laura.vimes@icloud.com (50 free credits)
- Cron jobs: 6am morning briefing, 6pm evening briefing (Europe/London), weekly cleanup (Sun 3am)
- Token crisis resolved (Feb 20): Weekly cleanup cron created to keep workspace under 300k words

## TotTrack
- Stack: Node/Express + React (Vite) + TypeScript on Replit
- Two projects: tottrack (original) and tot-track-standard (the main one)
- URL: tot-track-standard.replit.app
- App ID for iOS: com.shapps.tottrack
- Expo/EAS setup complete (Replit agent did it 2026-02-11), TESTFLIGHT.md created
- IDOR fixed, API routes fixed, security/data integrity fixes all deployed
- Reserved VM deployment (0.5 vCPU / 2 GiB RAM)
- Next step: Steven downloads to Laura's Mac → EAS build → TestFlight

## LeadBlitz Migration (2026-02-16)
- GitHub repo: github.com/lauravimes/leadblitz (PUBLIC, main branch)
- Local clone: /Users/lauravimes/.openclaw/workspace/leadblitz-code
- 69 files: main.py (4,206 lines), 27 helpers, static/, templates/
- Replit still hosting leadblitz.co — GitHub is dev copy
- Next: deploy staging to Railway/Render → Steven tests → fix bugs → flip DNS
- Secrets needed from Replit: SESSION_SECRET, ADMIN_PASSWORD, SMTP_*, STRIPE_*, NEON_DATABASE_URL, GA_MEASUREMENT_ID, ENCRYPTION_KEY, GOOGLE_MAPS_API_KEY, HUNTER_API_KEY, OPENAI_API_KEY
- Configs: BASE_URL=https://leadblitz.co, CALENDLY_LINK=https://cal.com/leadblitz/demo, FROM_EMAIL=sh@shapplications.com

## Reddit Automation
- Daily cron job: noon UK, 2-3 comments/day on r/webdesign, r/nocode, r/smallbusiness, r/freelance
- Cron ID: 9f6d434a-547a-41f8-b7d3-6f4542a5fb11
- Account: u/Steven-Leadblitz (openclaw browser profile)
- LESSON: Don't let Reddit slip — Steven expects consistent cadence

## LeadBlitz Users
- User #8: choudharykartik87@gmail.com — Karthick Periyasamy, Prodeets Chennai, B2B lead gen pro (likely competitor/evaluator)
- User #9: aniket@thedashmedia.com — Dash Media (digital marketing agency), Feb 19 2026
- Registration bug: signup grants 50 credits instead of 200. Hardcoded somewhere in register route. NOT YET FIXED.

## LeadBlitz Testing Status (as of 2026-02-14)
- Search: ✅ | Scoring: ✅ | SMS: ✅ | Registration: ✅ | Stripe: ✅
- Email: ✅ SMTP config, AI generation, send-single-email ALL WORKING on prod
- SMTP Fix: ✅ No longer hangs (5s timeout, save-first, provider always set)
- CSV Import: ✅ | Twilio webhook: ✅ | Password reset: ✅ | Blog: ✅ (3 articles live)
- 🔴 Campaign filter broken: dropdown doesn't filter leads table (fix prompt submitted to Replit agent, awaiting)
- 🔴 IDOR still present: users can see other users' leads
- ⚠️ Logout doesn't redirect to login page
- ⚠️ Website enrichment times out
- Production test accounts: `laura.vimes@icloud.com`/`NewTest2026!` (ID 6, 1000 credits)
- Laura's API session token: user_id 6, ~30 day expiry
- Managed print campaign UUID: `c527051e-6c3c-43f2-822a-548b5508a50b` (10 leads)

## Cefer Partnership
- Call with Cefer CEO scheduled week of 10 Feb 2026
- Prep doc: `/leadblitz/cefer-call-prep.md`
- Goal: per-call API pricing ($0.01-0.03/enrichment) for decision-maker data + technographics
- Key question: does Cefer have good coverage of local SMBs?
- Fallback: People Data Labs
- Steven asked to think about technographics Replit prompt — drafted and ready

## LinkedIn
- Company page: linkedin.com/company/leadblitzco (ID: 111341855)
- Managed via openclaw browser (Steven's personal LinkedIn account)
- Page setup: logo ✅, about section ✅, 7 specialties ✅, tagline ✅
- Cron jobs: AM post (9am UK), PM post (2pm UK), weekly content prep (Sun 8pm)
- Schedule tracker: `memory/linkedin-schedule.md`
- Steven has Premium LinkedIn account, 157 profile viewers
- Analytics (2026-02-14): 927 impressions (870 sponsored), 6 followers, organic reach very low
- Best post: 1,056 impressions, 4.55% engagement (sponsored)
- GA: 8 users/week, 92% direct traffic, only 1 LinkedIn social visit — funnel needs work

## Outreach Campaign (2026-02-14)
- Using LeadBlitz to find web design agencies → pitch them LeadBlitz (dog-fooding!)
- Targets: 50 agencies each in London, LA, Bangalore
- Email angle: COMPLIMENT their score, pitch tool for finding THEIR clients
- Offering 500 free credits trial
- Laura's account has 1000 credits for this
- Sub-agent spawned on Opus to run full campaign

## Browser Setup
- Use `profile="openclaw"` for ALL web tasks (Reddit, LinkedIn, Replit)
- No Chrome relay needed — openclaw browser is default
- LinkedIn: logged in as Steven Hallissey FCA (shaca147@gmail.com)
- Reddit: logged in as u/Steven-Leadblitz
- LinkedIn post technique: JS innerHTML injection into `.ql-editor` (type/slowly times out on long text)
- Replit agent textarea: React-controlled, can't set via DOM — Steven must paste prompts manually

## Cal.com
- URL: cal.com/leadblitz/demo
- Login: shaca147@gmail.com / LB!Cal2026Demo
- Event: "LeadBlitz Demo" (30 min, Cal Video, Mon-Fri 9am-5pm Europe/London)
- ⚠️ Host shows "Laura Vimes" — needs changing to Steven

## Key Documents
- /dinoroars/aso-plan.md — Full ASO & marketing plan
- /dinoroars/reddit-strategy.md — Reddit marketing playbook
- /leadblitz/launch-plan.md — Full launch & marketing plan
- /leadblitz/competitive-analysis.md — Apollo/Jeeva/Cefer analysis (pending)
- /projects/status.md — Project status board (attached to every briefing)
