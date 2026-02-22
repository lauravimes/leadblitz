#!/usr/bin/env node
// Score websites using AI analysis for Round 4 leads

const fs = require('fs');
const https = require('https');
const http = require('http');

const leads = JSON.parse(fs.readFileSync('round4-raw-leads.json', 'utf8'));

// Function to fetch website content
function fetchWebsite(url, timeout = 10000) {
    return new Promise((resolve, reject) => {
        try {
            const parsedUrl = new URL(url);
            const mod = parsedUrl.protocol === 'https:' ? https : http;
            
            const req = mod.get(url, { 
                timeout,
                headers: { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' }
            }, res => {
                if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
                    return fetchWebsite(res.headers.location, timeout).then(resolve).catch(reject);
                }
                
                let data = '';
                res.on('data', d => { 
                    data += d; 
                    if (data.length > 100000) { // Limit to 100KB
                        req.destroy(); 
                        resolve(data); 
                    } 
                });
                res.on('end', () => resolve(data));
                res.on('error', reject);
            });
            
            req.on('error', reject);
            req.on('timeout', () => { 
                req.destroy(); 
                reject(new Error('timeout')); 
            });
        } catch (e) {
            reject(e);
        }
    });
}

// Simple scoring algorithm based on website analysis
function scoreWebsite(html, url) {
    let score = 50; // Base score
    const reasons = [];
    
    if (!html) {
        return { score: 25, reasons: ['Website inaccessible or no content found'] };
    }
    
    const lowerHtml = html.toLowerCase();
    
    // Check for HTTPS
    if (url.startsWith('https://')) {
        score += 10;
        reasons.push('SSL certificate active (+10)');
    } else {
        score -= 10;
        reasons.push('No SSL certificate (-10)');
    }
    
    // Check for mobile responsiveness indicators
    if (lowerHtml.includes('viewport') || lowerHtml.includes('responsive') || lowerHtml.includes('@media')) {
        score += 8;
        reasons.push('Mobile responsive design indicators (+8)');
    }
    
    // Check for modern frameworks/technologies
    if (lowerHtml.includes('react') || lowerHtml.includes('vue') || lowerHtml.includes('angular') || lowerHtml.includes('bootstrap')) {
        score += 5;
        reasons.push('Modern web technologies detected (+5)');
    }
    
    // Check for SEO elements
    let seoCount = 0;
    if (lowerHtml.includes('<title>') && !lowerHtml.includes('<title></title>')) {
        seoCount++;
        reasons.push('Title tag present');
    }
    if (lowerHtml.includes('meta name="description"')) {
        seoCount++;
        reasons.push('Meta description present');
    }
    if (lowerHtml.includes('<h1>')) {
        seoCount++;
        reasons.push('H1 headings present');
    }
    
    score += seoCount * 3;
    
    // Check for contact information
    if (lowerHtml.includes('contact') || lowerHtml.includes('email') || lowerHtml.includes('@')) {
        score += 5;
        reasons.push('Contact information visible (+5)');
    }
    
    // Check for social media links
    if (lowerHtml.includes('facebook') || lowerHtml.includes('twitter') || lowerHtml.includes('linkedin') || lowerHtml.includes('instagram')) {
        score += 3;
        reasons.push('Social media presence (+3)');
    }
    
    // Check for portfolio/work examples
    if (lowerHtml.includes('portfolio') || lowerHtml.includes('work') || lowerHtml.includes('projects') || lowerHtml.includes('case stud')) {
        score += 8;
        reasons.push('Portfolio/work examples visible (+8)');
    }
    
    // Page size penalty for very large pages
    if (html.length > 200000) {
        score -= 5;
        reasons.push('Large page size may affect load times (-5)');
    }
    
    // Check for jQuery (slightly outdated but still functional)
    if (lowerHtml.includes('jquery')) {
        score += 2;
        reasons.push('jQuery library detected (+2)');
    }
    
    // Cap score between 15 and 95
    score = Math.max(15, Math.min(95, score));
    
    return { score: Math.round(score), reasons };
}

function generateScoreReasoning(score, reasons) {
    let reasoning = `Website scored ${score}/100. `;
    
    if (score >= 80) {
        reasoning += "Excellent website with strong technical foundation. ";
    } else if (score >= 65) {
        reasoning += "Good website with solid fundamentals. ";
    } else if (score >= 50) {
        reasoning += "Decent website with room for improvement. ";
    } else if (score >= 35) {
        reasoning += "Basic website with several areas needing attention. ";
    } else {
        reasoning += "Website needs significant improvements. ";
    }
    
    reasoning += "Key findings: " + reasons.join(', ') + ".";
    return reasoning;
}

async function scoreAllLeads() {
    console.log('Starting website scoring for Round 4 leads...');
    
    let totalScored = 0;
    let totalFailed = 0;
    
    // Process all cities
    for (const [cityKey, cityLeads] of Object.entries(leads)) {
        console.log(`\nScoring ${cityLeads.length} leads in ${cityKey}...`);
        
        for (let i = 0; i < cityLeads.length; i++) {
            const lead = cityLeads[i];
            process.stdout.write(`[${i+1}/${cityLeads.length}] ${lead.name}: `);
            
            try {
                const html = await fetchWebsite(lead.website);
                const { score, reasons } = scoreWebsite(html, lead.website);
                
                lead.score = score;
                lead.score_reasoning = generateScoreReasoning(score, reasons);
                lead.score_status = 'scored';
                lead.score_fail_reason = null;
                
                console.log(`${score}/100 ✓`);
                totalScored++;
                
                // Rate limit: wait 1 second between requests
                await new Promise(resolve => setTimeout(resolve, 1000));
                
            } catch (error) {
                lead.score = 35; // Default low score for inaccessible sites
                lead.score_reasoning = `Unable to access website for analysis. ${error.message}`;
                lead.score_status = 'scored_with_issues';
                lead.score_fail_reason = error.message;
                
                console.log(`Failed (${error.message}) - assigned 35/100`);
                totalFailed++;
            }
        }
    }
    
    // Save updated leads
    fs.writeFileSync('round4-scored-leads.json', JSON.stringify(leads, null, 2));
    
    console.log(`\n=== SCORING COMPLETE ===`);
    console.log(`Successfully scored: ${totalScored} leads`);
    console.log(`Failed/inaccessible: ${totalFailed} leads`);
    console.log(`Total leads: ${totalScored + totalFailed}`);
    console.log('Results saved to round4-scored-leads.json');
}

// Run the scoring
scoreAllLeads().catch(console.error);