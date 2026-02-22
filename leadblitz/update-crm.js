#!/usr/bin/env node
const fs = require('fs');
const crm = JSON.parse(fs.readFileSync('leadblitz/outreach-crm.json', 'utf8'));
const leads = JSON.parse(fs.readFileSync('leadblitz/round2-final-leads.json', 'utf8'));
const sendResults = JSON.parse(fs.readFileSync('leadblitz/round2-send-results.json', 'utf8'));

const today = new Date().toISOString().split('T')[0];
const sentEmails = new Set(sendResults.sent.map(s => s.email));
const existingEmails = new Set(crm.contacts.map(c => c.email));

let newCount = 0;
for (const city of ['pune', 'new_york', 'manchester']) {
  for (const lead of leads[city]) {
    if (!existingEmails.has(lead.email)) {
      crm.contacts.push({
        name: lead.name,
        email: lead.email,
        city: lead.city,
        website: lead.website,
        sent: sentEmails.has(lead.email) ? today : null,
        status: sentEmails.has(lead.email) ? "sent" : "new",
        reply: null,
        notes: `Round 2 - ${lead.city} campaign. Score: ${lead.score || 'N/A'}. PDF audit attached.`,
        round: 2
      });
      newCount++;
    }
  }
}

// Update stats
crm.stats.total_contacted = crm.contacts.filter(c => c.status === 'sent').length;
crm.stats.sent = crm.contacts.filter(c => c.status === 'sent').length;
crm.stats.round2_sent = sendResults.sent.length;
crm.stats.round2_failed = sendResults.failed.length;
crm.stats.round2_pune = leads.pune.length;
crm.stats.round2_new_york = leads.new_york.length;
crm.stats.round2_manchester = leads.manchester.length;
crm.meta.last_updated = new Date().toISOString();
crm.meta.round2_notes = `Round 2 complete: ${sendResults.sent.length} emails sent via himalaya with PDF audit reports attached. Pune: ${leads.pune.length}, New York: ${leads.new_york.length}, Manchester: ${leads.manchester.length}.`;

fs.writeFileSync('leadblitz/outreach-crm.json', JSON.stringify(crm, null, 2));
console.log(`CRM updated: ${newCount} new contacts added. Total contacts: ${crm.contacts.length}. Total sent: ${crm.stats.sent}.`);
