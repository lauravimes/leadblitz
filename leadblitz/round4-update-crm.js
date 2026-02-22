#!/usr/bin/env node
// Update CRM with Round 4 campaign results - mark as 'sent'

const fs = require('fs');

function updateCRM() {
    console.log('Updating CRM with Round 4 campaign results...');
    
    // Load existing CRM data
    const crm = JSON.parse(fs.readFileSync('outreach-crm.json', 'utf8'));
    
    // Load Round 4 send results
    if (!fs.existsSync('round4-send-results.json')) {
        console.log('Error: round4-send-results.json not found. Run email sending first.');
        return;
    }
    
    const results = JSON.parse(fs.readFileSync('round4-send-results.json', 'utf8'));
    
    // Update meta information
    crm.meta.last_updated = new Date().toISOString();
    crm.meta.round4_notes = `Round 4 complete: ${results.summary.sent} emails sent across Sydney (${results.summary.cities.sydney}), Cape Town (${results.summary.cities.cape_town}), Glasgow (${results.summary.cities.glasgow}). Used v2 AI audit template with HTML report attachments.`;
    
    // Add all successfully sent contacts to CRM
    let newContacts = 0;
    let updatedContacts = 0;
    
    results.sent_details.forEach(sentLead => {
        // Check if contact already exists
        const existingIndex = crm.contacts.findIndex(c => c.email === sentLead.email);
        
        const contactData = {
            name: sentLead.name,
            email: sentLead.email,
            city: sentLead.city,
            sent: new Date().toISOString().split('T')[0], // Today's date
            status: 'sent',
            reply: null,
            notes: `Round 4 campaign - Score: ${sentLead.score}/100`,
            score: sentLead.score,
            lead_id: sentLead.id,
            campaign: 'round4',
            template_version: 'v2_ai_audit'
        };
        
        if (existingIndex >= 0) {
            // Update existing contact
            crm.contacts[existingIndex] = { ...crm.contacts[existingIndex], ...contactData };
            crm.contacts[existingIndex].notes += ` | Updated Round 4: ${new Date().toISOString().split('T')[0]}`;
            updatedContacts++;
        } else {
            // Add new contact
            crm.contacts.push(contactData);
            newContacts++;
        }
    });
    
    // Also track failed sends for reference
    results.failed_details.forEach(failedLead => {
        const existingIndex = crm.contacts.findIndex(c => c.email === failedLead.email);
        
        if (existingIndex < 0) { // Only add if not already exists
            crm.contacts.push({
                name: failedLead.name,
                email: failedLead.email,
                city: failedLead.city,
                sent: null,
                status: 'send_failed',
                reply: null,
                notes: `Round 4 send failed: ${failedLead.error}`,
                lead_id: failedLead.id,
                campaign: 'round4',
                template_version: 'v2_ai_audit'
            });
        }
    });
    
    // Sort contacts by sent date (newest first)
    crm.contacts.sort((a, b) => {
        if (!a.sent) return 1;
        if (!b.sent) return -1;
        return new Date(b.sent) - new Date(a.sent);
    });
    
    // Save updated CRM
    fs.writeFileSync('outreach-crm.json', JSON.stringify(crm, null, 2));
    
    console.log(`\n=== CRM UPDATE COMPLETE ===`);
    console.log(`New contacts added: ${newContacts}`);
    console.log(`Existing contacts updated: ${updatedContacts}`);
    console.log(`Total contacts in CRM: ${crm.contacts.length}`);
    console.log(`Failed sends tracked: ${results.failed_details.length}`);
    console.log('CRM updated and saved to outreach-crm.json');
    
    // Generate summary stats
    const statusCounts = crm.contacts.reduce((acc, contact) => {
        acc[contact.status] = (acc[contact.status] || 0) + 1;
        return acc;
    }, {});
    
    console.log(`\nCRM Status Summary:`);
    Object.entries(statusCounts).forEach(([status, count]) => {
        console.log(`- ${status}: ${count} contacts`);
    });
    
    return {
        newContacts,
        updatedContacts,
        totalContacts: crm.contacts.length,
        statusCounts
    };
}

if (require.main === module) {
    updateCRM();
}

module.exports = updateCRM;