#!/usr/bin/env node
// Round 3 Pipeline: Deduplicate, save leads, generate PDFs
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Load all search results
const chicago1 = JSON.parse(fs.readFileSync('/tmp/lb-cookies.txt', 'utf8').length ? '[]' : '[]');

// We'll load leads from the API responses saved during search
// For now, let's work with what we have from the search calls

// Read the API cookie file to verify login
console.log('Starting Round 3 pipeline...');

// Function to deduplicate leads by website domain
function dedupeLeads(leads) {
  const seen = new Map();
  return leads.filter(l => {
    if (!l.website) return false;
    try {
      const domain = new URL(l.website).hostname.replace('www.', '');
      if (seen.has(domain)) return false;
      seen.set(domain, true);
      return true;
    } catch {
      return true;
    }
  });
}

console.log('Pipeline script ready - will be called from main orchestrator');
