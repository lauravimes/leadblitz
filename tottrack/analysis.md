# TotTrack Standard — Analysis & Go-to-Market

## What I Found

**Tech:** React + Vite + TypeScript + Tailwind + Drizzle ORM, ElevenLabs TTS for audio activities
**54 activities** across 7 developmental categories: cognitive, creative, custom, language, motor, sensory, social
**Age range:** 12-60 months (1-5 years)
**Features:** Child profiles, milestone tracking, growth tracking, development reports (SEND screening), activities with audio, care tasks, emotion strategies, emergency info, onboarding, privacy/consent flows
**Monetisation:** 14-day free trial → subscription (Stripe + Apple IAP + Google Play billing already wired)
**Mobile prep:** Expo/React Native folder exists with eas.json

## Issues Found
- Published deployment (tottrackstandard.replit.app) returns 404 — needs republishing
- Email field is NOT NULL in DB but marked "Optional" on registration form — will crash if left blank
- 27 users already in the DB (from testing presumably)
