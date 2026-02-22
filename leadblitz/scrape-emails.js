#!/usr/bin/env node
// Scrape emails from agency websites
const https = require('https');
const http = require('http');
const fs = require('fs');

const leads = JSON.parse(fs.readFileSync('leadblitz/round2-leads-raw.json', 'utf8'));

// Get all leads that need emails
const needEmails = [];
for (const city of ['new_york', 'manchester']) {
  for (const lead of leads[city]) {
    if (!lead.email) needEmails.push(lead);
  }
}

console.log(`Need to scrape emails for ${needEmails.length} leads`);

function fetchPage(url, timeout = 8000) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http;
    const req = mod.get(url, { 
      timeout,
      headers: { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)' }
    }, res => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        return fetchPage(res.headers.location, timeout).then(resolve).catch(reject);
      }
      let data = '';
      res.on('data', d => { data += d; if (data.length > 200000) { req.destroy(); resolve(data); } });
      res.on('end', () => resolve(data));
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
  });
}

function extractEmails(html) {
  const emailRegex = /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g;
  const matches = html.match(emailRegex) || [];
  // Filter out image files, css files etc
  return [...new Set(matches.filter(e => 
    !e.match(/\.(png|jpg|jpeg|gif|svg|css|js|woff|ttf)$/i) &&
    !e.includes('example.com') &&
    !e.includes('sentry') &&
    !e.includes('webpack') &&
    e.length < 60
  ))];
}

async function scrapeEmails(lead) {
  const urls = [lead.website];
  // Also try /contact page
  const base = lead.website.replace(/\/$/, '');
  urls.push(base + '/contact');
  urls.push(base + '/contact-us');
  
  const allEmails = [];
  for (const url of urls) {
    try {
      const html = await fetchPage(url);
      const emails = extractEmails(html);
      allEmails.push(...emails);
    } catch (e) {
      // ignore
    }
  }
  
  const unique = [...new Set(allEmails)];
  // Prefer info@, hello@, contact@ emails
  const preferred = unique.find(e => /^(info|hello|contact|sales|enquir|team|hi)@/i.test(e));
  return preferred || unique[0] || null;
}

async function main() {
  const results = {};
  for (const lead of needEmails) {
    process.stdout.write(`Scraping ${lead.name} (${lead.website})... `);
    try {
      const email = await scrapeEmails(lead);
      if (email) {
        console.log(`✓ ${email}`);
        lead.email = email;
        results[lead.name] = email;
      } else {
        console.log('✗ no email found');
      }
    } catch (e) {
      console.log(`✗ error: ${e.message}`);
    }
  }
  
  // Save updated leads
  fs.writeFileSync('leadblitz/round2-leads-raw.json', JSON.stringify(leads, null, 2));
  console.log(`\nScraped ${Object.keys(results).length} emails from ${needEmails.length} leads`);
  console.log(JSON.stringify(results, null, 2));
}

main().catch(console.error);
