#!/usr/bin/env node
// Generate PDF audit reports for Round 4 leads

const fs = require('fs');

function generateAuditHTML(lead) {
    const score = lead.score || 35;
    const companyName = lead.name;
    const website = lead.website;
    const reasoning = lead.score_reasoning || "Website analysis completed.";
    
    // Score-based recommendations
    let recommendations = [];
    let strengths = [];
    
    if (score >= 75) {
        strengths.push("Strong overall website performance");
        strengths.push("Good technical foundation");
        recommendations.push("Continue monitoring performance metrics");
        recommendations.push("Consider advanced conversion optimization");
    } else if (score >= 50) {
        strengths.push("Solid basic website structure");
        recommendations.push("Optimize page load speeds");
        recommendations.push("Improve mobile responsiveness");
        recommendations.push("Enhance SEO metadata");
    } else {
        recommendations.push("Implement SSL certificate");
        recommendations.push("Add mobile-responsive design");
        recommendations.push("Improve website content structure");
        recommendations.push("Optimize for search engines");
    }
    
    // Score color coding
    let scoreColor = '#e74c3c'; // Red
    let scoreGrade = 'F';
    
    if (score >= 90) {
        scoreColor = '#27ae60';
        scoreGrade = 'A+';
    } else if (score >= 80) {
        scoreColor = '#2ecc71';
        scoreGrade = 'A';
    } else if (score >= 70) {
        scoreColor = '#f39c12';
        scoreGrade = 'B';
    } else if (score >= 60) {
        scoreColor = '#e67e22';
        scoreGrade = 'C';
    } else if (score >= 50) {
        scoreColor = '#d35400';
        scoreGrade = 'D';
    }
    
    return `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Website Audit Report - ${companyName}</title>
    <style>
        body { font-family: 'Arial', sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-radius: 8px; }
        .header { text-align: center; margin-bottom: 40px; border-bottom: 3px solid #3498db; padding-bottom: 20px; }
        .logo { font-size: 28px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }
        .subtitle { color: #7f8c8d; font-size: 16px; }
        .company-info { background: #ecf0f1; padding: 20px; border-radius: 6px; margin-bottom: 30px; }
        .score-section { text-align: center; margin: 30px 0; }
        .score-circle { width: 120px; height: 120px; border-radius: 50%; margin: 0 auto 20px; display: flex; align-items: center; justify-content: center; color: white; font-size: 32px; font-weight: bold; }
        .score-details { background: #f8f9fa; padding: 25px; border-radius: 6px; margin: 20px 0; }
        .recommendations { background: #e8f4fd; border-left: 4px solid #3498db; padding: 20px; margin: 20px 0; }
        .strengths { background: #d4edda; border-left: 4px solid #27ae60; padding: 20px; margin: 20px 0; }
        .list-item { margin: 8px 0; padding-left: 15px; position: relative; }
        .list-item:before { content: "•"; position: absolute; left: 0; color: #3498db; font-weight: bold; }
        .cta { background: #3498db; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; font-weight: bold; text-align: center; }
        .footer { margin-top: 40px; text-align: center; color: #7f8c8d; font-size: 12px; border-top: 1px solid #ecf0f1; padding-top: 20px; }
        h2 { color: #2c3e50; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }
        h3 { color: #34495e; margin-top: 25px; }
        .grade { font-size: 20px; font-weight: bold; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">LeadBlitz</div>
            <div class="subtitle">Website Performance Audit Report</div>
        </div>
        
        <div class="company-info">
            <h2>Audit Report for ${companyName}</h2>
            <p><strong>Website:</strong> ${website}</p>
            <p><strong>Report Generated:</strong> ${new Date().toLocaleDateString()}</p>
        </div>
        
        <div class="score-section">
            <div class="score-circle" style="background-color: ${scoreColor};">
                ${score}
            </div>
            <div class="grade" style="color: ${scoreColor};">Grade: ${scoreGrade}</div>
            <p>Overall Website Performance Score</p>
        </div>
        
        <div class="score-details">
            <h3>Analysis Summary</h3>
            <p>${reasoning}</p>
        </div>
        
        ${strengths.length > 0 ? `
        <div class="strengths">
            <h3>✓ Key Strengths</h3>
            ${strengths.map(strength => `<div class="list-item">${strength}</div>`).join('')}
        </div>
        ` : ''}
        
        <div class="recommendations">
            <h3>🎯 Recommended Improvements</h3>
            ${recommendations.map(rec => `<div class="list-item">${rec}</div>`).join('')}
        </div>
        
        <div style="text-align: center; margin: 40px 0;">
            <h3>Want reports like this for YOUR prospects?</h3>
            <p>LeadBlitz generates personalized website audit reports for any business, helping you demonstrate value and win more clients.</p>
            <a href="https://leadblitz.co" class="cta">Try LeadBlitz Free — 500 Credits</a>
        </div>
        
        <div class="footer">
            <p>This report was generated by LeadBlitz - AI-powered lead generation and website analysis.</p>
            <p>© 2026 SH Applications. All rights reserved.</p>
        </div>
    </div>
</body>
</html>`;
}

async function generateAllPDFs() {
    console.log('Starting PDF generation for Round 4 leads...');
    
    // First check if scored leads exist
    if (!fs.existsSync('round4-scored-leads.json')) {
        console.log('Waiting for scoring to complete...');
        return;
    }
    
    const leads = JSON.parse(fs.readFileSync('round4-scored-leads.json', 'utf8'));
    let totalGenerated = 0;
    
    // Ensure pdf-reports directory exists
    if (!fs.existsSync('pdf-reports')) {
        fs.mkdirSync('pdf-reports', { recursive: true });
    }
    
    // Process all cities
    for (const [cityKey, cityLeads] of Object.entries(leads)) {
        console.log(`\nGenerating PDFs for ${cityLeads.length} leads in ${cityKey}...`);
        
        for (let i = 0; i < cityLeads.length; i++) {
            const lead = cityLeads[i];
            const safeName = lead.name.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 40);
            
            try {
                const html = generateAuditHTML(lead);
                const htmlPath = `pdf-reports/${safeName}.html`;
                
                fs.writeFileSync(htmlPath, html);
                console.log(`[${i+1}/${cityLeads.length}] Generated ${safeName}.html`);
                totalGenerated++;
                
            } catch (error) {
                console.log(`[${i+1}/${cityLeads.length}] Failed ${safeName}: ${error.message}`);
            }
        }
    }
    
    console.log(`\n=== PDF GENERATION COMPLETE ===`);
    console.log(`Generated: ${totalGenerated} HTML reports`);
    console.log('HTML files saved to pdf-reports/ directory');
    console.log('Note: For production, these would be converted to PDF using a service like wkhtmltopdf or Puppeteer');
}

// Run PDF generation
generateAllPDFs().catch(console.error);