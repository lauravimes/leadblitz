#!/usr/bin/env node
// Send personalized outreach emails to all leads using himalaya-send wrapper
const fs = require('fs');
const { execSync } = require('child_process');
const path = require('path');

const leads = JSON.parse(fs.readFileSync('leadblitz/round2-final-leads.json', 'utf8'));
const allLeads = [...leads.pune, ...leads.new_york, ...leads.manchester];

const sent = [];
const failed = [];
let skipCount = 0;

function getStrength(lead) {
  const score = lead.score || 55;
  if (score >= 70) return "Strong mobile responsiveness and solid page speed.";
  if (score >= 50) return "Good SSL security and reasonable online presence.";
  if (score >= 30) return "Your SSL is active and we found social media profiles linked.";
  return "We found your site and ran our full analysis.";
}

function generateEmailHTML(lead) {
  const companyName = lead.name;
  const strength = getStrength(lead);
  
  return `<p>Hi there,</p>

<p>We used our AI audit tool to score <strong>${companyName}</strong>&rsquo;s website &mdash; the full report is attached.</p>

<p>You'll see your site scored well. ${strength}</p>

<p>Now imagine sending a report like this to YOUR target customers &mdash; except theirs isn't quite so strong. You can show them exactly where they're losing visitors, where their SEO is falling short, and how you can add value. No more generic pitches &mdash; just hard data that sells your expertise for you.</p>

<p>That's what <strong>LeadBlitz</strong> does. It finds local businesses, scores their websites with AI, and generates personalised outreach so you can land clients with proof, not promises.</p>

<p>We're in early access and I'd love to offer you <strong>500 free credits</strong> to try it &mdash; no strings attached.</p>

<p>Check it out: <a href="https://leadblitz.co">https://leadblitz.co</a></p>

<p>Happy to walk you through it if you'd prefer &mdash; just reply to this email.</p>

<p>Best,<br/>
Laura Vimes<br/>
Chief of Staff, SH Applications<br/>
laura.vimes@icloud.com</p>

<p style="font-size:11px; color:#999;">If you'd prefer not to hear from us, simply reply with "unsubscribe" and we'll remove you immediately.</p>`;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
  console.log(`Sending outreach to ${allLeads.length} leads...`);
  
  for (let i = 0; i < allLeads.length; i++) {
    const lead = allLeads[i];
    
    if (!lead.email) {
      console.log(`[${i+1}/${allLeads.length}] SKIP ${lead.name} - no email`);
      skipCount++;
      continue;
    }
    
    const safeName = lead.name.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 40);
    const pdfPath = path.resolve(`leadblitz/pdf-reports/${safeName}.pdf`);
    const subject = `We scored your website — here's the report, ${lead.name}`;
    const bodyHtml = generateEmailHTML(lead);
    
    console.log(`[${i+1}/${allLeads.length}] Sending to ${lead.name} (${lead.email})...`);
    
    try {
      // Build MML message with attachment
      let mml = `From: Laura Vimes <laura.vimes@icloud.com>\nTo: ${lead.email}\nSubject: ${subject}\n\n<#part type=text/html>\n${bodyHtml}\n</#part>`;
      
      if (fs.existsSync(pdfPath)) {
        const b64 = fs.readFileSync(pdfPath).toString('base64');
        mml += `\n<#part filename="${safeName}_Audit_Report.pdf" type=application/pdf>\n${b64}\n</#part>`;
      }
      
      // Write temp file and send
      const tmpFile = `/tmp/leadblitz_email_${i}.mml`;
      fs.writeFileSync(tmpFile, mml);
      
      const result = execSync(`cat "${tmpFile}" | himalaya message send 2>&1`, { timeout: 30000 }).toString();
      console.log(`  ✓ Sent! ${result.trim()}`);
      sent.push({ name: lead.name, email: lead.email, city: lead.city });
      
      // Clean up
      fs.unlinkSync(tmpFile);
      
      // Rate limit: wait 2 seconds between emails
      await sleep(2000);
      
    } catch (e) {
      console.log(`  ✗ Failed: ${e.message?.substring(0, 100)}`);
      failed.push({ name: lead.name, email: lead.email, city: lead.city, error: e.message?.substring(0, 100) });
    }
  }
  
  console.log(`\n=== SUMMARY ===`);
  console.log(`Sent: ${sent.length}`);
  console.log(`Failed: ${failed.length}`);
  console.log(`Skipped (no email): ${skipCount}`);
  
  // Save results
  fs.writeFileSync('leadblitz/round2-send-results.json', JSON.stringify({ sent, failed, skipCount, timestamp: new Date().toISOString() }, null, 2));
  console.log('Results saved to leadblitz/round2-send-results.json');
}

main().catch(console.error);
