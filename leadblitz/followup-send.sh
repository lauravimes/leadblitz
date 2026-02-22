#!/bin/bash
# Follow-up email sender for LeadBlitz outreach
# Reads contacts from CRM JSON, sends personalised follow-ups via himalaya

CRM="/Users/lauravimes/.openclaw/workspace/leadblitz/outreach-crm.json"
LOG="/Users/lauravimes/.openclaw/workspace/memory/outreach-followup.md"
SENT=0
FAILED=0
SKIPPED=0

echo "# Outreach Follow-up Log — $(date '+%Y-%m-%d %H:%M')" > "$LOG"
echo "" >> "$LOG"
echo "## Follow-up Emails Sent" >> "$LOG"
echo "" >> "$LOG"

# Extract contacts with status "sent"
CONTACTS=$(python3 -c "
import json
with open('$CRM') as f:
    data = json.load(f)
for i, c in enumerate(data['contacts']):
    if c['status'] == 'sent':
        name = c['name'].replace(\"'\", \"\\\\'\")
        print(f\"{i}|{c['email']}|{name}\")
")

TOTAL=$(echo "$CONTACTS" | wc -l | tr -d ' ')
echo "Sending follow-ups to $TOTAL contacts..."
echo "Total eligible: $TOTAL" >> "$LOG"
echo "" >> "$LOG"

while IFS='|' read -r IDX EMAIL COMPANY; do
    [ -z "$EMAIL" ] && continue

    SUBJECT="Quick follow-up — ${COMPANY}'s website audit"

    BODY="<html><body style='font-family: Arial, sans-serif; font-size: 14px; color: #333;'>
<p>Hi there,</p>

<p>I ran an AI audit on ${COMPANY}'s website last week and put together a quick report — thought you might find it interesting. Your site scored well, which says a lot about the quality of work you do.</p>

<p>Here's the thing though — imagine sending that same kind of report to <em>your</em> prospective clients. Showing them exactly where their site is falling short on SEO, speed, or mobile experience — and how you can fix it. No more generic pitches. Just hard data that sells your expertise.</p>

<p>That's exactly what <a href='https://leadblitz.co'>LeadBlitz</a> does. I'd love to offer you <strong>500 free credits</strong> to try it — no strings attached.</p>

<p>Worth a look? → <a href='https://leadblitz.co'>leadblitz.co</a></p>

<p>Best,<br>
Laura Vimes<br>
Chief of Staff, SH Applications<br>
laura.vimes@icloud.com</p>
</body></html>"

    # Send via himalaya
    MSG="From: Laura Vimes <laura.vimes@icloud.com>
To: ${EMAIL}
Subject: ${SUBJECT}

<#part type=text/html>
${BODY}
</#part>"

    if echo "$MSG" | himalaya message send 2>/dev/null; then
        echo "✅ ${COMPANY} (${EMAIL})" >> "$LOG"
        SENT=$((SENT + 1))
        # Update CRM status
        python3 -c "
import json
with open('$CRM') as f:
    data = json.load(f)
data['contacts'][${IDX}]['status'] = 'follow-up-sent'
data['contacts'][${IDX}]['notes'] = (data['contacts'][${IDX}].get('notes') or '') + ' | Follow-up sent $(date +%Y-%m-%d)'
with open('$CRM', 'w') as f:
    json.dump(data, f, indent=2)
"
    else
        echo "❌ FAILED: ${COMPANY} (${EMAIL})" >> "$LOG"
        FAILED=$((FAILED + 1))
    fi

    # Rate limit: 2 second delay between sends
    sleep 2

done <<< "$CONTACTS"

echo "" >> "$LOG"
echo "## Summary" >> "$LOG"
echo "- Sent: $SENT" >> "$LOG"
echo "- Failed: $FAILED" >> "$LOG"
echo "- Date: $(date '+%Y-%m-%d %H:%M')" >> "$LOG"

echo "Done. Sent: $SENT, Failed: $FAILED"
