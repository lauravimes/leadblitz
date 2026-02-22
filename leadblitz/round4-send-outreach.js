#!/usr/bin/env node
// Send Round 4 outreach emails to Sydney, Cape Town, Glasgow agencies

const fs = require('fs');
const { execSync } = require('child_process');
const path = require('path');

// Check if scored leads exist
if (!fs.existsSync('round4-scored-leads.json')) {
    console.log('Error: round4-scored-leads.json not found. Run scoring first.');
    process.exit(1);
}

const leads = JSON.parse(fs.readFileSync('round4-scored-leads.json', 'utf8'));

// Flatten all leads into a single array with city info
const allLeads = [];
Object.entries(leads).forEach(([cityKey, cityLeads]) => {
    cityLeads.forEach(lead => {
        lead.cityKey = cityKey;
        allLeads.push(lead);
    });
});

console.log(`Round 4 Outreach: ${allLeads.length} total leads across Sydney (${leads.sydney.length}), Cape Town (${leads.cape_town.length}), Glasgow (${leads.glasgow.length})`);

const sent = [];
const failed = [];
let skipCount = 0;

function getStrength(lead) {
    const score = lead.score || 35;
    if (score >= 80) return "Excellent SSL security, strong mobile responsiveness, and solid page speed metrics.";
    if (score >= 65) return "Good SSL security, mobile optimization, and decent technical foundation.";
    if (score >= 50) return "SSL certificate active and reasonable technical structure in place.";
    if (score >= 35) return "We found your site and completed our comprehensive technical analysis.";
    return "We analyzed your website presence and technical setup.";
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
    console.log(`\nStarting Round 4 email outreach...`);
    console.log('Using proven "AI audit" template that has been driving traffic\n');
    
    for (let i = 0; i < allLeads.length; i++) {
        const lead = allLeads[i];
        
        if (!lead.email) {
            console.log(`[${i+1}/${allLeads.length}] SKIP ${lead.name} (${lead.cityKey}) - no email`);
            skipCount++;
            continue;
        }
        
        const safeName = lead.name.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 40);
        const htmlReportPath = path.resolve(`leadblitz/pdf-reports/${safeName}.html`);
        const subject = `We scored your website — here's the report, ${lead.name}`;
        const bodyHtml = generateEmailHTML(lead);
        
        console.log(`[${i+1}/${allLeads.length}] Sending to ${lead.name} (${lead.cityKey}) - ${lead.email}...`);
        
        try {
            // Build MML message
            let mml = `From: Laura Vimes <laura.vimes@icloud.com>\nTo: ${lead.email}\nSubject: ${subject}\n\n<#part type=text/html>\n${bodyHtml}\n</#part>`;
            
            // Attach HTML report if it exists (in production, this would be a PDF)
            if (fs.existsSync(htmlReportPath)) {
                const reportContent = fs.readFileSync(htmlReportPath, 'utf8');
                const b64 = Buffer.from(reportContent).toString('base64');
                mml += `\n<#part filename="${safeName}_Website_Audit_Report.html" type=text/html>\n${b64}\n</#part>`;
            }
            
            // Write temp file and send
            const tmpFile = `/tmp/leadblitz_round4_${i}.mml`;
            fs.writeFileSync(tmpFile, mml);
            
            const result = execSync(`cat "${tmpFile}" | himalaya message send 2>&1`, { timeout: 30000 }).toString();
            console.log(`  ✓ Sent! ${result.trim()}`);
            sent.push({ 
                name: lead.name, 
                email: lead.email, 
                city: lead.cityKey, 
                score: lead.score,
                id: lead.id 
            });
            
            // Clean up
            fs.unlinkSync(tmpFile);
            
            // Rate limit: 2 seconds between emails
            await sleep(2000);
            
        } catch (e) {
            console.log(`  ✗ Failed: ${e.message?.substring(0, 100)}`);
            failed.push({ 
                name: lead.name, 
                email: lead.email, 
                city: lead.cityKey, 
                error: e.message?.substring(0, 100),
                id: lead.id 
            });
        }
    }
    
    console.log(`\n=== ROUND 4 CAMPAIGN SUMMARY ===`);
    console.log(`Total leads processed: ${allLeads.length}`);
    console.log(`Successfully sent: ${sent.length}`);
    console.log(`Failed to send: ${failed.length}`);
    console.log(`Skipped (no email): ${skipCount}`);
    console.log(`\nBreakdown by city:`);
    console.log(`- Sydney: ${leads.sydney.length} leads`);
    console.log(`- Cape Town: ${leads.cape_town.length} leads`);  
    console.log(`- Glasgow: ${leads.glasgow.length} leads`);
    
    // Save detailed results
    const results = {
        campaign: 'Round 4 - Sydney/Cape Town/Glasgow',
        timestamp: new Date().toISOString(),
        summary: {
            total_leads: allLeads.length,
            sent: sent.length,
            failed: failed.length,
            skipped: skipCount,
            cities: {
                sydney: leads.sydney.length,
                cape_town: leads.cape_town.length,
                glasgow: leads.glasgow.length
            }
        },
        sent_details: sent,
        failed_details: failed,
        email_template: 'v2_ai_audit',
        attachment: 'html_audit_report'
    };
    
    fs.writeFileSync('leadblitz/round4-send-results.json', JSON.stringify(results, null, 2));
    console.log('\nDetailed results saved to round4-send-results.json');
    
    return results;
}

if (require.main === module) {
    main().catch(console.error);
}

module.exports = main;