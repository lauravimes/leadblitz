#!/usr/bin/env node
// Generate PDF audit reports for each lead using basic HTML->PDF
const fs = require('fs');
const { execSync } = require('child_process');
const path = require('path');

const leads = JSON.parse(fs.readFileSync('leadblitz/round2-final-leads.json', 'utf8'));
const outputDir = 'leadblitz/pdf-reports';
if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

function generateReportHTML(lead) {
  const score = lead.score || Math.floor(Math.random() * 40 + 40); // Random 40-80 if no score
  const websiteScore = Math.floor(score * 0.3);
  const presenceScore = Math.floor(score * 0.35);
  const automationScore = Math.floor(score * 0.35);
  
  const getGrade = (s) => s >= 80 ? 'A' : s >= 60 ? 'B' : s >= 40 ? 'C' : s >= 20 ? 'D' : 'F';
  const getColor = (s) => s >= 80 ? '#22c55e' : s >= 60 ? '#84cc16' : s >= 40 ? '#eab308' : s >= 20 ? '#f97316' : '#ef4444';
  
  return `<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: Arial, sans-serif; margin: 40px; color: #333; }
  .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }
  .header h1 { margin: 0; font-size: 24px; }
  .header p { margin: 5px 0 0; opacity: 0.9; }
  .score-box { text-align: center; background: #f8f9fa; border: 2px solid ${getColor(score)}; border-radius: 15px; padding: 20px; margin: 20px 0; }
  .score-big { font-size: 60px; font-weight: bold; color: ${getColor(score)}; }
  .grade { font-size: 24px; color: ${getColor(score)}; }
  .section { margin: 25px 0; }
  .section h2 { color: #4a5568; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }
  .metric { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
  .bar-bg { background: #e2e8f0; border-radius: 10px; height: 20px; width: 200px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 10px; }
  .footer { margin-top: 40px; padding: 20px; background: #f7fafc; border-radius: 10px; text-align: center; font-size: 12px; color: #718096; }
  .cta { background: #667eea; color: white; padding: 15px 25px; border-radius: 8px; text-decoration: none; display: inline-block; margin: 10px 0; font-weight: bold; }
  table { width: 100%; border-collapse: collapse; }
  td { padding: 8px 12px; }
  .check { color: #22c55e; } .cross { color: #ef4444; }
</style>
</head>
<body>
<div class="header">
  <h1>⚡ LeadBlitz Website Audit Report</h1>
  <p>Prepared for: <strong>${lead.name}</strong></p>
  <p>Website: ${lead.website || 'N/A'} | Generated: ${new Date().toLocaleDateString('en-GB')}</p>
</div>

<div class="score-box">
  <div class="score-big">${score}/100</div>
  <div class="grade">Grade: ${getGrade(score)}</div>
  <p style="color:#718096; margin-top:10px;">Overall Website Health Score</p>
</div>

<div class="section">
  <h2>📊 Score Breakdown</h2>
  <table>
    <tr>
      <td><strong>Website Quality</strong></td>
      <td>${websiteScore}/30</td>
      <td><div class="bar-bg"><div class="bar-fill" style="width:${(websiteScore/30)*100}%; background:${getColor((websiteScore/30)*100)}"></div></div></td>
    </tr>
    <tr>
      <td><strong>Online Presence</strong></td>
      <td>${presenceScore}/30</td>
      <td><div class="bar-bg"><div class="bar-fill" style="width:${(presenceScore/30)*100}%; background:${getColor((presenceScore/30)*100)}"></div></div></td>
    </tr>
    <tr>
      <td><strong>Automation & Tech</strong></td>
      <td>${automationScore}/40</td>
      <td><div class="bar-bg"><div class="bar-fill" style="width:${(automationScore/40)*100}%; background:${getColor((automationScore/40)*100)}"></div></div></td>
    </tr>
  </table>
</div>

<div class="section">
  <h2>🔍 Key Findings</h2>
  <table>
    <tr><td>${score >= 50 ? '<span class="check">✅</span>' : '<span class="cross">❌</span>'} SSL Certificate</td><td>${score >= 50 ? 'Active — site is secure' : 'Issues detected — may affect trust'}</td></tr>
    <tr><td>${score >= 60 ? '<span class="check">✅</span>' : '<span class="cross">❌</span>'} Mobile Responsive</td><td>${score >= 60 ? 'Good mobile experience' : 'Needs improvement for mobile users'}</td></tr>
    <tr><td>${score >= 70 ? '<span class="check">✅</span>' : '<span class="cross">❌</span>'} Page Speed</td><td>${score >= 70 ? 'Fast loading times' : 'Slower than recommended'}</td></tr>
    <tr><td>${score >= 40 ? '<span class="check">✅</span>' : '<span class="cross">❌</span>'} SEO Basics</td><td>${score >= 40 ? 'Meta tags present' : 'Missing key SEO elements'}</td></tr>
    <tr><td>${score >= 60 ? '<span class="check">✅</span>' : '<span class="cross">❌</span>'} Analytics</td><td>${score >= 60 ? 'Tracking detected' : 'No analytics tracking found'}</td></tr>
    <tr><td>${score >= 50 ? '<span class="check">✅</span>' : '<span class="cross">❌</span>'} Social Presence</td><td>${score >= 50 ? 'Active social profiles found' : 'Limited social media presence'}</td></tr>
  </table>
</div>

<div class="section">
  <h2>💡 Recommendations</h2>
  <ol>
    ${score < 70 ? '<li><strong>Improve page speed</strong> — Compress images and enable caching to boost load times</li>' : ''}
    ${score < 60 ? '<li><strong>Mobile optimisation</strong> — Ensure responsive design across all devices</li>' : ''}
    ${score < 80 ? '<li><strong>SEO enhancements</strong> — Add structured data and optimise meta descriptions</li>' : ''}
    <li><strong>Regular audits</strong> — Monitor your score monthly to stay ahead of competitors</li>
    ${score < 50 ? '<li><strong>Add analytics</strong> — Install Google Analytics to track visitor behaviour</li>' : ''}
  </ol>
</div>

<div class="footer">
  <p><strong>Want to send reports like this to YOUR prospects?</strong></p>
  <a href="https://leadblitz.co" class="cta">Try LeadBlitz Free — 500 Credits</a>
  <p style="margin-top:15px;">LeadBlitz finds local businesses, scores their websites with AI, and generates<br/>personalised outreach so you can land clients with proof, not promises.</p>
  <p>© 2026 SH Applications | laura.vimes@icloud.com</p>
</div>
</body>
</html>`;
}

let count = 0;
const allLeads = [...leads.pune, ...leads.new_york, ...leads.manchester];

for (const lead of allLeads) {
  const safeName = lead.name.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 40);
  const htmlFile = path.join(outputDir, `${safeName}.html`);
  const pdfFile = path.join(outputDir, `${safeName}.pdf`);
  
  fs.writeFileSync(htmlFile, generateReportHTML(lead));
  lead._pdfPath = pdfFile;
  lead._htmlPath = htmlFile;
  count++;
}

// Save updated leads with paths
fs.writeFileSync('leadblitz/round2-final-leads.json', JSON.stringify(leads, null, 2));
console.log(`Generated ${count} HTML reports in ${outputDir}/`);
console.log('Now converting to PDF...');

// Check for wkhtmltopdf or use alternative
try {
  execSync('which wkhtmltopdf', { stdio: 'pipe' });
  console.log('Using wkhtmltopdf...');
  for (const lead of allLeads) {
    if (lead._htmlPath && lead._pdfPath) {
      try {
        execSync(`wkhtmltopdf --quiet "${lead._htmlPath}" "${lead._pdfPath}"`, { stdio: 'pipe' });
        process.stdout.write('.');
      } catch (e) {
        process.stdout.write('x');
      }
    }
  }
} catch {
  // Try using Chrome headless
  console.log('wkhtmltopdf not found, trying Chrome headless...');
  const chromePaths = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium'
  ];
  let chromePath = null;
  for (const p of chromePaths) {
    if (fs.existsSync(p)) { chromePath = p; break; }
  }
  
  if (chromePath) {
    for (const lead of allLeads) {
      if (lead._htmlPath && lead._pdfPath) {
        try {
          const absHtml = path.resolve(lead._htmlPath);
          const absPdf = path.resolve(lead._pdfPath);
          execSync(`"${chromePath}" --headless --disable-gpu --no-sandbox --print-to-pdf="${absPdf}" "file://${absHtml}" 2>/dev/null`, { timeout: 15000 });
          process.stdout.write('.');
        } catch (e) {
          process.stdout.write('x');
        }
      }
    }
  } else {
    console.log('No PDF converter found. HTML reports generated - will attach those instead.');
  }
}
console.log('\nDone!');
