#!/usr/bin/env node
const https = require('https');
const http = require('http');

function fetchPage(url, timeout = 8000) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http;
    const req = mod.get(url, { timeout, headers: { 'User-Agent': 'Mozilla/5.0' } }, res => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        const loc = res.headers.location.startsWith('http') ? res.headers.location : new URL(res.headers.location, url).href;
        return fetchPage(loc, timeout).then(resolve).catch(reject);
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
  const matches = html.match(/[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g) || [];
  return [...new Set(matches.filter(e => !e.match(/\.(png|jpg|gif|svg|css|js|woff)$/i) && !e.includes('sentry') && !e.includes('webpack') && e.length < 60))];
}

const targets = [
  // More Manchester
  {name: "Splitpixel", website: "https://www.splitpixel.co.uk/", city: "Manchester"},
  {name: "Ahoy Creative", website: "https://ahoy.co.uk/", city: "Manchester"},
  {name: "CTI Digital", website: "https://ctidigital.com/", city: "Manchester"},
  {name: "Bamboo Manchester", website: "https://www.bamboomanchester.uk/", city: "Manchester"},
  {name: "Sood Agency", website: "https://sood.agency/", city: "Manchester"},
  {name: "First Internet", website: "https://www.firstinternet.co.uk/", city: "Manchester"},
  {name: "Studio RAV", website: "https://www.studiorav.co.uk/", city: "Manchester"},
  {name: "WebSoft Dreams", website: "https://www.websoftdreams.com/", city: "Manchester"},
  {name: "Bubble Design", website: "https://www.bubbledesign.co.uk/", city: "Manchester"},
  {name: "CodeDesign", website: "https://codedesign.org/", city: "Manchester"},
  {name: "GetProcopy", website: "https://getprocopy.com/", city: "Manchester"},
  {name: "DMac Media", website: "https://dmacmedia.com/", city: "Manchester"},
  // More NYC
  {name: "Flipside Group", website: "https://flipsidegroup.com/", city: "New York"},
  {name: "Burst Digital", website: "https://burstdgtl.com/", city: "New York"},
  {name: "Big City NYC", website: "https://bigcitynyc.com/", city: "New York"},
  {name: "AdvancedTechCo", website: "https://www.advancedtechco.com/", city: "New York"},
  {name: "ProStrategix", website: "https://www.prostrategix.com/", city: "New York"},
  {name: "OSMOS", website: "https://www.osmos.co/", city: "New York"},
  {name: "Oraiko", website: "https://www.oraiko.com/", city: "New York"},
  {name: "Bracha Designs", website: "https://brachadesigns.com/", city: "New York"},
  {name: "Sedulous", website: "https://www.sedulous.co/", city: "New York"},
  {name: "Geekin NY", website: "https://geekinny.com/", city: "New York"},
  {name: "Leadige Agency", website: "https://leadige.agency/", city: "New York"},
  // More Pune
  {name: "Jay Shinde Web", website: "https://jayshinde.com/", city: "Pune"},
  {name: "BrandWeb India", website: "https://brandwebindia.com/", city: "Pune"},
  {name: "WebPulse India", website: "https://www.webpulseindia.com/", city: "Pune"},
];

async function main() {
  const results = [];
  for (const t of targets) {
    process.stdout.write(`${t.name} (${t.website})... `);
    try {
      const urls = [t.website, t.website.replace(/\/$/, '') + '/contact', t.website.replace(/\/$/, '') + '/contact-us'];
      let email = null;
      for (const url of urls) {
        try {
          const html = await fetchPage(url);
          const emails = extractEmails(html);
          const preferred = emails.find(e => /^(info|hello|contact|sales|enquir|team|hi|get|support)@/i.test(e));
          if (preferred || emails[0]) { email = preferred || emails[0]; break; }
        } catch {}
      }
      if (email) {
        console.log(`✓ ${email}`);
        results.push({...t, email});
      } else {
        console.log('✗');
      }
    } catch (e) {
      console.log(`✗ ${e.message}`);
    }
  }
  console.log(JSON.stringify(results, null, 2));
}
main();
