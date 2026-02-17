let currentLeads = [];
let activeCampaignId = null;
let currentUser = null;
let apiKeysStatus = {};
let currentLeadsView = null;
let selectedLeadIds = new Set();
let sourceFilterActive = 'all';
let csvImportFile = null;
let csvImportParsedData = null;
let csvImportPollingId = null;

// Prevent navigation shortcuts (End, Home, etc.) when typing in input/textarea
document.addEventListener('keydown', (e) => {
    const activeElement = document.activeElement;
    const isTyping = activeElement && (
        activeElement.tagName === 'INPUT' || 
        activeElement.tagName === 'TEXTAREA' || 
        activeElement.isContentEditable
    );
    
    if (isTyping && ['End', 'Home', 'PageUp', 'PageDown'].includes(e.key)) {
        e.stopPropagation();
    }
}, true);

// Landing page state
let isLandingPageVisible = true;

// Landing page functions
function showLandingPage() {
    const landingPage = document.getElementById('landing-page');
    const topNav = document.querySelector('.top-nav');
    const container = document.querySelector('.container');
    const authModal = document.getElementById('authModal');
    
    if (landingPage) landingPage.classList.add('active');
    if (topNav) topNav.style.display = 'none';
    if (container) container.style.display = 'none';
    if (authModal) authModal.style.display = 'none';
    
    // Update landing nav based on login status
    const dashboardLink = document.getElementById('landingDashboardLink');
    const loginBtn = document.getElementById('landingLoginBtn');
    const registerBtn = document.getElementById('landingRegisterBtn');
    const landingCreditsLink = document.getElementById('landingCreditsLink');
    const landingCreditsBalance = document.getElementById('landingCreditsBalance');
    const landingLogoutLink = document.getElementById('landingLogoutLink');
    
    if (currentUser) {
        if (dashboardLink) dashboardLink.style.display = 'inline';
        if (landingCreditsLink) landingCreditsLink.style.display = 'inline-flex';
        if (landingCreditsBalance) landingCreditsBalance.textContent = userCredits.balance || 0;
        if (landingLogoutLink) landingLogoutLink.style.display = 'inline';
        if (loginBtn) loginBtn.style.display = 'none';
        if (registerBtn) registerBtn.style.display = 'none';
    } else {
        if (dashboardLink) dashboardLink.style.display = 'none';
        if (landingCreditsLink) landingCreditsLink.style.display = 'none';
        if (landingLogoutLink) landingLogoutLink.style.display = 'none';
        if (loginBtn) loginBtn.style.display = 'inline-block';
        if (registerBtn) registerBtn.style.display = 'inline-block';
    }
    
    isLandingPageVisible = true;
}

function goToDashboard() {
    hideLandingPage();
    showPage('dashboard');
}

function hideLandingPage() {
    const landingPage = document.getElementById('landing-page');
    const topNav = document.querySelector('.top-nav');
    const container = document.querySelector('.container');
    
    if (landingPage) landingPage.classList.remove('active');
    if (topNav) topNav.style.display = '';
    if (container) container.style.display = '';
    
    isLandingPageVisible = false;
}

function showLoginFromLanding() {
    hideLandingPage();
    showAuthModal();
    showLogin();
}

function showRegisterFromLanding() {
    hideLandingPage();
    showAuthModal();
    showRegister();
}

function togglePricingPeriod() {
    const toggle = document.getElementById('pricingToggle');
    const monthlyLabel = document.getElementById('monthlyLabel');
    const annualLabel = document.getElementById('annualLabel');
    const isAnnual = toggle.classList.toggle('annual');
    
    monthlyLabel.classList.toggle('active', !isAnnual);
    annualLabel.classList.toggle('active', isAnnual);
    
    document.querySelectorAll('.pricing-amount .price').forEach(el => {
        el.textContent = isAnnual ? el.dataset.annual : el.dataset.monthly;
    });
    document.querySelectorAll('.pricing-amount .period').forEach(el => {
        el.textContent = isAnnual ? el.dataset.annual : el.dataset.monthly;
    });
}

function scrollToSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function toggleLandingMobileMenu() {
    const navLinks = document.querySelector('.landing-nav-links');
    if (navLinks) {
        navLinks.classList.toggle('mobile-active');
    }
}

// Sorting state
let sortConfig = {
    field: null,  // 'name', 'email', 'score', 'stage'
    direction: 'asc'  // 'asc' or 'desc'
};

// Current score breakdown (for email composition)
let currentScoreBreakdown = null;

// Pipeline stage order for sorting
const STAGE_ORDER = {
    'new': 1,
    'contacted': 2,
    'replied': 3,
    'meeting': 4,
    'closed_won': 5,
    'closed_lost': 6
};

function toggleMobileMenu() {
    const navMenu = document.getElementById('navMenu');
    navMenu.classList.toggle('active');
}

function toggleDropdown(dropdownId) {
    const allDropdowns = document.querySelectorAll('.dropdown');
    const dropdownMenu = document.getElementById(dropdownId);
    const clickedDropdown = dropdownMenu.closest('.dropdown');
    
    allDropdowns.forEach(dropdown => {
        if (dropdown !== clickedDropdown) {
            dropdown.classList.remove('active');
        }
    });
    
    clickedDropdown.classList.toggle('active');
}

function closeAllDropdowns() {
    document.querySelectorAll('.dropdown').forEach(d => d.classList.remove('active'));
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeAllDropdowns();
    }
});

function showPage(pageName) {
    const allPages = document.querySelectorAll('.page');
    allPages.forEach(page => page.classList.remove('active'));
    
    const targetPage = document.getElementById(`page-${pageName}`);
    if (targetPage) {
        targetPage.classList.add('active');
    }
    
    const allDropdowns = document.querySelectorAll('.dropdown');
    allDropdowns.forEach(dropdown => dropdown.classList.remove('active'));
    
    const navMenu = document.getElementById('navMenu');
    navMenu.classList.remove('active');
    
    if (typeof gtag === 'function') {
        gtag('event', 'page_view', {
            page_title: pageName,
            page_path: '/' + pageName
        });
    }
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
    
    // Prevent accidental immediate clicks on mobile after navigation
    if (window.innerWidth <= 768) {
        const newPageButtons = targetPage.querySelectorAll('button');
        newPageButtons.forEach(btn => {
            btn.style.pointerEvents = 'none';
        });
        setTimeout(() => {
            newPageButtons.forEach(btn => {
                btn.style.pointerEvents = 'auto';
            });
        }, 300);
    }
    
    if (pageName === 'dashboard') {
        loadLeads();
        loadAnalytics();
    }
    
    if (pageName === 'settings') {
        loadUserSettings();
    }
}

function showDashboard() {
    showPage('dashboard');
}

async function showAllLeads() {
    currentLeadsView = 'all';
    activeCampaignId = null;
    showPage('leads');
    try {
        const response = await fetch('/api/leads?view=all');
        const data = await response.json();
        if (response.ok) {
            currentLeads = data.leads;
            renderLeadsTable();
            document.getElementById('loadMoreBtn').style.display = 'none';
            showStatus('leadsStatus', `Showing all ${data.leads.length} leads across all campaigns`, 'info');
            setTimeout(() => showStatus('leadsStatus', '', ''), 3000);
        }
    } catch (error) {
        console.error('Error loading all leads:', error);
    }
}

async function showStrongLeads() {
    currentLeadsView = 'strong';
    activeCampaignId = null;
    showPage('leads');
    try {
        const response = await fetch('/api/leads?view=strong');
        const data = await response.json();
        if (response.ok) {
            currentLeads = data.leads;
            renderLeadsTable();
            document.getElementById('loadMoreBtn').style.display = 'none';
            showStatus('leadsStatus', `Showing ${data.leads.length} strong leads (score < 30) - best sales opportunities`, 'success');
            setTimeout(() => showStatus('leadsStatus', '', ''), 4000);
        }
    } catch (error) {
        console.error('Error loading strong leads:', error);
    }
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('.dropdown') && !e.target.closest('.mobile-menu-toggle')) {
        const allDropdowns = document.querySelectorAll('.dropdown');
        allDropdowns.forEach(dropdown => dropdown.classList.remove('active'));
    }
    
    if (!e.target.closest('.nav-menu') && !e.target.closest('.mobile-menu-toggle')) {
        const navMenu = document.getElementById('navMenu');
        if (navMenu) {
            navMenu.classList.remove('active');
        }
    }
});

async function loadCampaigns() {
    try {
        const response = await fetch('/api/campaigns');
        const data = await response.json();

        if (response.ok && data.campaigns.length > 0) {
            const dropdown = document.getElementById('campaignDropdown');
            dropdown.innerHTML = '<option value="">-- Select a Campaign --</option>';
            
            data.campaigns.forEach(campaign => {
                const option = document.createElement('option');
                option.value = campaign.id;
                option.textContent = `${campaign.name} (${campaign.lead_count} leads) - ${new Date(campaign.created_at).toLocaleDateString()}`;
                dropdown.appendChild(option);
            });
            
            if (data.active_campaign_id) {
                dropdown.value = data.active_campaign_id;
                updateCampaignInfo(data.campaigns.find(c => c.id === data.active_campaign_id));
            }
        }
    } catch (error) {
        console.error('Error loading campaigns:', error);
    }
}

async function switchCampaign() {
    const campaignId = document.getElementById('campaignDropdown').value;
    
    if (!campaignId) {
        updateCampaignInfo(null);
        return;
    }

    try {
        const response = await fetch(`/api/campaigns/${campaignId}`);
        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }
        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            console.error('switchCampaign: non-JSON response, status:', response.status);
            return;
        }
        const data = await response.json();

        if (response.ok) {
            updateCampaignInfo(data.campaign);
        }
    } catch (error) {
        console.error('Error fetching campaign info:', error);
    }
}

async function viewSelectedCampaignLeads() {
    const campaignId = document.getElementById('campaignDropdown').value;
    
    if (!campaignId) {
        alert('Please select a campaign first');
        return;
    }
    
    try {
        const activateResponse = await fetch(`/api/campaigns/${campaignId}/activate`, {
            method: 'POST'
        });
        
        if (activateResponse.status === 401) {
            window.location.href = '/login';
            return;
        }
        const activateContentType = activateResponse.headers.get('content-type') || '';
        if (!activateContentType.includes('application/json')) {
            console.error('viewSelectedCampaignLeads: non-JSON response, status:', activateResponse.status);
            alert('Session expired. Please log in again.');
            window.location.href = '/login';
            return;
        }
        
        const activateData = await activateResponse.json();
        if (!activateResponse.ok) {
            console.error('Failed to activate campaign:', activateData);
            return;
        }

        const response = await fetch(`/api/leads?campaign_id=${encodeURIComponent(campaignId)}`);
        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }
        const data = await response.json();
        
        if (response.ok) {
            showPage('leads');
            currentLeads = data.leads || [];
            activeCampaignId = campaignId;
            renderLeadsTable();
            loadAnalytics();
            updateCampaignInfo(activateData.campaign);
            
            const loadMoreBtn = document.getElementById('loadMoreBtn');
            if (activateData.campaign && activateData.campaign.has_more) {
                loadMoreBtn.style.display = 'inline-block';
            } else {
                loadMoreBtn.style.display = 'none';
            }
            
            const allDropdowns = document.querySelectorAll('.dropdown');
            allDropdowns.forEach(dropdown => dropdown.classList.remove('active'));
            const navMenu = document.getElementById('navMenu');
            navMenu.classList.remove('active');
            
            showStatus('leadsStatus', `Showing ${currentLeads.length} leads from "${activateData.campaign.name}"`, 'success');
            setTimeout(() => showStatus('leadsStatus', '', ''), 3000);
        } else {
            alert(data.detail || 'Failed to load campaign leads');
        }
    } catch (error) {
        console.error('Error viewing campaign leads:', error);
        alert('Error loading campaign leads. Please try again.');
    }
}

function updateCampaignInfo(campaign) {
    const campaignInfoDiv = document.getElementById('campaignInfo');
    if (campaign) {
        const createdAt = new Date(campaign.created_at).toLocaleDateString();
        campaignInfoDiv.innerHTML = `
            <div style="background: rgba(139, 92, 246, 0.1); padding: 8px; border-radius: 6px; margin-top: 8px;">
                <strong>✓ ${campaign.name}</strong><br>
                <small>${campaign.lead_count} leads • Created ${createdAt}</small>
            </div>
        `;
    } else {
        campaignInfoDiv.textContent = '';
    }
}

async function deleteSelectedCampaign() {
    const campaignId = document.getElementById('campaignDropdown').value;
    
    if (!campaignId) {
        alert('Please select a campaign first');
        return;
    }
    
    const dropdown = document.getElementById('campaignDropdown');
    const selectedOption = dropdown.options[dropdown.selectedIndex];
    const campaignName = selectedOption ? selectedOption.textContent : 'this campaign';
    
    if (!confirm(`Delete "${campaignName}"? This will also delete all leads in this campaign. This cannot be undone.`)) {
        return;
    }
    
    try {
        console.log('Attempting to delete campaign:', campaignId);
        const response = await fetch(`/api/campaigns/${campaignId}`, {
            method: 'DELETE',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log('Delete response status:', response.status);
        
        if (response.ok) {
            alert('Campaign deleted successfully');
            document.getElementById('campaignDropdown').value = '';
            updateCampaignInfo(null);
            await loadCampaigns();
            await loadLeads();
            await loadAnalytics();
        } else {
            let errorMsg = 'Failed to delete campaign';
            try {
                const error = await response.json();
                errorMsg = error.detail || errorMsg;
            } catch (e) {
                errorMsg = `Server returned status ${response.status}`;
            }
            alert(`Error: ${errorMsg}`);
        }
    } catch (error) {
        console.error('Error deleting campaign:', error);
        alert(`Error deleting campaign: ${error.message || 'Network error'}`);
    }
}

async function searchLeads() {
    const businessType = document.getElementById('businessType').value;
    const location = document.getElementById('location').value;
    const limit = parseInt(document.getElementById('limit').value) || 20;

    if (!businessType || !location) {
        showStatus('searchStatus', 'Please enter business type and location', 'error');
        return;
    }

    showLoadingOverlay('Searching for Businesses', 'Finding leads via Google Places API...');
    showStatus('searchStatus', 'Searching... 0 seconds elapsed', 'info');
    
    // Start elapsed time counter
    let elapsedSeconds = 0;
    const timerInterval = setInterval(() => {
        elapsedSeconds++;
        showStatus('searchStatus', `Searching... ${elapsedSeconds} seconds elapsed`, 'info');
    }, 1000);
    
    // Create AbortController for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ business_type: businessType, location, limit, auto_score: document.getElementById('autoScoreCheckbox')?.checked ?? true }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        clearInterval(timerInterval);

        const data = await safeJsonParse(response);

        if (response.ok) {
            const allDropdowns = document.querySelectorAll('.dropdown');
            allDropdowns.forEach(dropdown => dropdown.classList.remove('active'));
            
            if (data.cached) {
                showStatus('searchStatus', `Loaded ${data.count} leads from existing campaign`, 'success');
                showToast(`Loaded ${data.count} leads from existing campaign`, 'success');
                currentLeads = data.leads;
                renderLeadsTable();
                loadAnalytics();
                loadCampaigns();
                showPage('leads');
            } else {
                const autoScore = document.getElementById('autoScoreCheckbox')?.checked ?? true;
                
                showProgressModal();
                updateProgress(1, `Found ${data.count} leads!`);
                showStatus('searchStatus', `Found ${data.count} leads! (${data.count} credits used)`, 'success');
                showToast(`Found ${data.count} new leads! ${data.count} credits used.`, 'success');
                currentLeads = data.leads;
                renderLeadsTable();
                loadAnalytics();
                loadCampaigns();
                loadCredits();
                showPage('leads');
                
                if (autoScore) {
                    await autoEnrichAndScoreWithProgress();
                } else {
                    await autoEnrichOnly();
                    closeProgressModal();
                }
            }
            
            const loadMoreBtn = document.getElementById('loadMoreBtn');
            if (data.campaign && data.campaign.has_more) {
                loadMoreBtn.style.display = 'inline-block';
            } else {
                loadMoreBtn.style.display = 'none';
            }
            
            setTimeout(() => showStatus('searchStatus', '', ''), 5000);
        } else {
            if (response.status === 404) {
                showSearchErrorPopup(data.detail || 'No businesses found. Try a different search or check the location spelling.');
                showToast('No businesses found for this search.', 'error');
            } else if (response.status === 402) {
                showToast(data.detail || 'Insufficient credits. Please purchase more credits.', 'error', 6000);
                showStatus('searchStatus', data.detail || 'Insufficient credits.', 'error');
            } else {
                showToast(data.detail || 'Search temporarily unavailable. Please try again.', 'error');
                showStatus('searchStatus', data.detail || 'Something went wrong. Please try again.', 'error');
            }
        }
    } catch (error) {
        clearTimeout(timeoutId);
        clearInterval(timerInterval);
        
        if (error.name === 'AbortError') {
            showToast('Search timed out. Try a more specific search.', 'error', 6000);
            showSearchErrorPopup('The search took too long and was cancelled after 60 seconds. Try searching for a more specific business type or a smaller location area.');
        } else {
            showToast('Search temporarily unavailable. Please try again.', 'error');
            showStatus('searchStatus', 'Something went wrong. Please try again.', 'error');
        }
    } finally {
        hideLoadingOverlay();
    }
}

function showToast(message, type = 'info', duration = 4000) {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span class="toast-message">${message}</span>`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('toast-hide');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function fillExampleSearch(businessType, location) {
    showPage('search');
    setTimeout(() => {
        const bizInput = document.getElementById('businessType');
        const locInput = document.getElementById('location');
        if (bizInput) bizInput.value = businessType;
        if (locInput) locInput.value = location;
    }, 100);
}

function showSearchErrorPopup(message) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.id = 'searchErrorOverlay';
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;justify-content:center;align-items:center;z-index:10000;';
    
    const modal = document.createElement('div');
    modal.style.cssText = 'background:white;border-radius:12px;padding:32px;max-width:450px;width:90%;text-align:center;box-shadow:0 10px 40px rgba(0,0,0,0.2);';
    
    modal.innerHTML = `
        <div style="font-size:48px;margin-bottom:16px;">⚠️</div>
        <h2 style="color:#333;margin-bottom:12px;font-size:20px;">Search Failed</h2>
        <p style="color:#666;line-height:1.6;margin-bottom:24px;">${message}</p>
        <button onclick="closeSearchErrorPopup()" style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;border:none;padding:12px 32px;border-radius:8px;font-size:16px;cursor:pointer;font-weight:500;">Try Again</button>
    `;
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) closeSearchErrorPopup();
    });
}

function closeSearchErrorPopup() {
    const overlay = document.getElementById('searchErrorOverlay');
    if (overlay) overlay.remove();
}

async function scoreLeads() {
    // Count leads that need scoring
    const leadsToScore = currentLeads.filter(l => l.website);
    const totalLeads = leadsToScore.length;
    
    if (totalLeads === 0) {
        showStatus('leadsStatus', 'No leads with websites to score', 'info');
        return;
    }
    
    // Show progress overlay with animated progress bar
    showScoringProgressOverlay(totalLeads);
    showStatus('leadsStatus', 'Scoring leads with AI... This may take a moment.', 'info');

    try {
        const response = await fetch('/api/score-leads', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await safeJsonParse(response);

        if (response.ok) {
            const successCount = data.count - (data.failed_count || 0);
            showStatus('leadsStatus', `Scored ${successCount} leads!`, 'success');
            currentLeads = data.leads;
            renderLeadsTable();
            loadAnalytics();
            loadCredits();
            
            // Show popup if there were failed leads
            if (data.failed_count > 0) {
                showScoringFailuresPopup(data.failed_count, data.failure_summary);
            }
        } else {
            showStatus('leadsStatus', `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('leadsStatus', `Error: ${error.message}`, 'error');
    } finally {
        hideScoringProgressOverlay();
    }
}

function showScoringProgressOverlay(totalLeads) {
    let overlay = document.getElementById('scoringProgressOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'scoringProgressOverlay';
        document.body.appendChild(overlay);
    }
    
    overlay.innerHTML = `
        <div style="
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        ">
            <div style="
                background: white;
                border-radius: 16px;
                padding: 32px 48px;
                text-align: center;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 400px;
                width: 90%;
            ">
                <div style="
                    width: 60px;
                    height: 60px;
                    border: 4px solid #e5e7eb;
                    border-top: 4px solid #4a6cf7;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 20px;
                "></div>
                
                <h3 style="margin: 0 0 8px; color: #111827; font-size: 1.25rem;">
                    Scoring Leads with AI
                </h3>
                
                <p id="scoringProgressText" style="margin: 0 0 20px; color: #6b7280; font-size: 0.95rem;">
                    Analyzing ${totalLeads} website${totalLeads > 1 ? 's' : ''}...
                </p>
                
                <div style="
                    background: #e5e7eb;
                    border-radius: 10px;
                    height: 12px;
                    overflow: hidden;
                    margin-bottom: 12px;
                ">
                    <div id="scoringProgressBar" style="
                        height: 100%;
                        background: linear-gradient(90deg, #4a6cf7, #6366f1, #8b5cf6);
                        background-size: 200% 100%;
                        animation: shimmer 2s ease-in-out infinite, grow 0.3s ease-out;
                        border-radius: 10px;
                        width: 0%;
                        transition: width 0.5s ease-out;
                    "></div>
                </div>
                
                <p id="scoringProgressPercent" style="margin: 0; color: #374151; font-weight: 600; font-size: 1.1rem;">
                    0%
                </p>
            </div>
        </div>
        <style>
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            @keyframes shimmer { 0%, 100% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } }
        </style>
    `;
    overlay.style.display = 'block';
    
    // Simulate progress (each lead takes ~3-8 seconds)
    const estimatedTimePerLead = 5000; // 5 seconds per lead
    const totalTime = totalLeads * estimatedTimePerLead;
    const updateInterval = 200; // Update every 200ms
    let elapsed = 0;
    
    window.scoringProgressInterval = setInterval(() => {
        elapsed += updateInterval;
        // Use an easing function to slow down as we approach 90%
        const linearProgress = Math.min(elapsed / totalTime, 0.9);
        const easedProgress = linearProgress * (2 - linearProgress); // Ease out
        const percent = Math.round(easedProgress * 100);
        
        const progressBar = document.getElementById('scoringProgressBar');
        const progressPercent = document.getElementById('scoringProgressPercent');
        const progressText = document.getElementById('scoringProgressText');
        
        if (progressBar) progressBar.style.width = percent + '%';
        if (progressPercent) progressPercent.textContent = percent + '%';
        
        // Update text based on progress
        if (progressText) {
            const leadsProcessed = Math.floor(linearProgress * totalLeads);
            if (percent < 30) {
                progressText.textContent = `Fetching website content...`;
            } else if (percent < 60) {
                progressText.textContent = `Analyzing with AI (${leadsProcessed + 1}/${totalLeads})...`;
            } else if (percent < 90) {
                progressText.textContent = `Generating insights...`;
            } else {
                progressText.textContent = `Finalizing scores...`;
            }
        }
        
        if (percent >= 90) {
            clearInterval(window.scoringProgressInterval);
        }
    }, updateInterval);
}

function hideScoringProgressOverlay() {
    // Complete the progress bar before hiding
    const progressBar = document.getElementById('scoringProgressBar');
    const progressPercent = document.getElementById('scoringProgressPercent');
    
    if (progressBar) progressBar.style.width = '100%';
    if (progressPercent) progressPercent.textContent = '100%';
    
    if (window.scoringProgressInterval) {
        clearInterval(window.scoringProgressInterval);
    }
    
    // Short delay to show 100% before hiding
    setTimeout(() => {
        const overlay = document.getElementById('scoringProgressOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }, 500);
}

function showScoringFailuresPopup(failedCount, failureSummary) {
    // Build failure reasons list
    let reasonsHtml = '';
    for (const [reason, leadNames] of Object.entries(failureSummary)) {
        reasonsHtml += `
            <div style="margin-bottom: 12px;">
                <div style="font-weight: 600; color: #374151; margin-bottom: 4px;">${reason}</div>
                <div style="color: #6b7280; font-size: 0.9rem; padding-left: 12px;">
                    ${leadNames.slice(0, 5).join(', ')}${leadNames.length > 5 ? ` and ${leadNames.length - 5} more` : ''}
                </div>
            </div>
        `;
    }
    
    const popupHtml = `
        <div id="scoringFailuresPopup" style="
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: fadeIn 0.2s ease-out;
        ">
            <div style="
                background: white;
                border-radius: 12px;
                padding: 24px;
                max-width: 480px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
            ">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                    <div style="
                        width: 40px;
                        height: 40px;
                        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 20px;
                    ">⚠️</div>
                    <h3 style="margin: 0; color: #111827; font-size: 1.25rem;">
                        ${failedCount} Lead${failedCount > 1 ? 's' : ''} Could Not Be Scored
                    </h3>
                </div>
                
                <div style="
                    background: #f0fdf4;
                    border: 1px solid #bbf7d0;
                    border-radius: 8px;
                    padding: 12px;
                    margin-bottom: 16px;
                    color: #166534;
                    font-weight: 500;
                ">
                    You have not been charged any credits for these leads.
                </div>
                
                <div style="margin-bottom: 20px;">
                    <div style="font-weight: 600; color: #111827; margin-bottom: 12px;">Reasons:</div>
                    ${reasonsHtml}
                </div>
                
                <div style="
                    background: #eff6ff;
                    border: 1px solid #bfdbfe;
                    border-radius: 8px;
                    padding: 12px;
                    margin-bottom: 20px;
                    color: #1e40af;
                    font-size: 0.9rem;
                ">
                    <strong>Tip:</strong> You can try scoring these leads again later. Some websites may be temporarily unavailable or have security measures that require manual review.
                </div>
                
                <button onclick="document.getElementById('scoringFailuresPopup').remove()" style="
                    width: 100%;
                    padding: 12px;
                    background: linear-gradient(135deg, #4a6cf7 0%, #3b5ce5 100%);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 1rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: transform 0.1s ease;
                " onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                    Got it
                </button>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', popupHtml);
}

async function loadLeads() {
    try {
        let url = '/api/leads';
        if (activeCampaignId) {
            url += `?campaign_id=${encodeURIComponent(activeCampaignId)}`;
        }
        const response = await fetch(url);
        const data = await response.json();

        if (response.ok) {
            currentLeads = data.leads;
            renderLeadsTable();
            loadAnalytics();
            
            const effectiveCampaignId = data.active_campaign_id || activeCampaignId;
            if (effectiveCampaignId) {
                activeCampaignId = effectiveCampaignId;
                const campaignResponse = await fetch(`/api/campaigns`);
                const campaignsData = await campaignResponse.json();
                const activeCampaign = campaignsData.campaigns.find(c => c.id === effectiveCampaignId);
                
                const loadMoreBtn = document.getElementById('loadMoreBtn');
                if (activeCampaign && activeCampaign.has_more) {
                    loadMoreBtn.style.display = 'inline-block';
                } else {
                    loadMoreBtn.style.display = 'none';
                }
                
                if (activeCampaign) {
                    updateCampaignInfo(activeCampaign);
                }
            }
            
            autoEnrichAndScore();
        }
    } catch (error) {
        console.error('Error loading leads:', error);
    }
}

async function autoEnrichAndScore() {
    if (currentLeads.length === 0) return;
    
    const leadsNeedingEmail = currentLeads.filter(lead => !lead.email && lead.website);
    const leadsNeedingScore = currentLeads.filter(lead => lead.score === 0);
    
    if (leadsNeedingEmail.length > 0) {
        showStatus('leadsStatus', `Auto-enriching emails for ${leadsNeedingEmail.length} leads...`, 'info');
        
        try {
            const leadIds = leadsNeedingEmail.map(l => l.id);
            const response = await fetch('/api/enrich-from-website', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lead_ids: leadIds })
            });
            
            const data = await response.json();
            
            if (response.ok && data.updated > 0) {
                showStatus('leadsStatus', `✓ Found emails for ${data.updated} leads`, 'success');
                let refreshUrl = '/api/leads';
                if (activeCampaignId) refreshUrl += `?campaign_id=${encodeURIComponent(activeCampaignId)}`;
                const refreshResponse = await fetch(refreshUrl);
                const refreshData = await refreshResponse.json();
                if (refreshResponse.ok) {
                    currentLeads = refreshData.leads;
                    renderLeadsTable();
                }
                setTimeout(() => showStatus('leadsStatus', '', ''), 5000);
            } else if (response.ok) {
                showStatus('leadsStatus', `No additional emails found from website scraping`, 'info');
                setTimeout(() => showStatus('leadsStatus', '', ''), 3000);
            }
        } catch (error) {
            console.error('Auto-enrich error:', error);
        }
    }
    
    if (leadsNeedingScore.length > 0) {
        showStatus('leadsStatus', `Auto-scoring ${leadsNeedingScore.length} leads with AI...`, 'info');
        
        try {
            const response = await fetch('/api/score-leads', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showStatus('leadsStatus', `✓ AI-scored ${data.count} leads`, 'success');
                currentLeads = data.leads;
                renderLeadsTable();
                loadAnalytics();
                setTimeout(() => showStatus('leadsStatus', '', ''), 3000);
            }
        } catch (error) {
            console.error('Auto-score error:', error);
        }
    }
}

async function autoEnrichOnly() {
    if (currentLeads.length === 0) return;
    
    const leadsNeedingEmail = currentLeads.filter(lead => !lead.email && lead.website);
    
    if (leadsNeedingEmail.length > 0) {
        updateProgress(2, `Extracting emails from ${leadsNeedingEmail.length} websites...`);
        
        try {
            const leadIds = leadsNeedingEmail.map(l => l.id);
            const response = await fetch('/api/enrich-from-website', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lead_ids: leadIds })
            });
            
            const data = await response.json();
            
            if (response.ok && data.updated > 0) {
                showStatus('leadsStatus', `Found emails for ${data.updated} leads!`, 'success');
                let refreshUrl = '/api/leads';
                if (activeCampaignId) refreshUrl += `?campaign_id=${encodeURIComponent(activeCampaignId)}`;
                const refreshResponse = await fetch(refreshUrl);
                const refreshData = await refreshResponse.json();
                if (refreshResponse.ok) {
                    currentLeads = refreshData.leads;
                    renderLeadsTable();
                }
            }
        } catch (error) {
            console.error('Auto-enrich error:', error);
        }
    }
    
    showStatus('leadsStatus', 'Leads ready! Click "Re-score All with AI" to score them.', 'info');
}

async function autoEnrichAndScoreWithProgress() {
    if (currentLeads.length === 0) {
        closeProgressModal();
        return;
    }
    
    const leadsNeedingEmail = currentLeads.filter(lead => !lead.email && lead.website);
    const leadsNeedingScore = currentLeads.filter(lead => lead.score === 0 && lead.website);
    
    // Stage 2: Email enrichment
    if (leadsNeedingEmail.length > 0) {
        updateProgress(2, `Extracting emails from ${leadsNeedingEmail.length} websites...`);
        
        try {
            const leadIds = leadsNeedingEmail.map(l => l.id);
            const response = await fetch('/api/enrich-from-website', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lead_ids: leadIds })
            });
            
            const data = await response.json();
            
            if (response.ok && data.updated > 0) {
                updateProgress(2, `Found emails for ${data.updated} leads!`);
                let refreshUrl = '/api/leads';
                if (activeCampaignId) refreshUrl += `?campaign_id=${encodeURIComponent(activeCampaignId)}`;
                const refreshResponse = await fetch(refreshUrl);
                const refreshData = await refreshResponse.json();
                if (refreshResponse.ok) {
                    currentLeads = refreshData.leads;
                    renderLeadsTable();
                }
            }
        } catch (error) {
            console.error('Auto-enrich error:', error);
        }
    } else {
        updateProgress(2, 'Email enrichment complete');
    }
    
    // Stage 3: Progressive AI scoring - score leads one by one with live updates
    if (leadsNeedingScore.length > 0) {
        let scored = 0;
        let failed = 0;
        const total = leadsNeedingScore.length;
        
        updateProgressWithDetail(3, `Scoring leads...`, scored, total);
        
        for (const lead of leadsNeedingScore) {
            try {
                const response = await fetch(`/api/score-lead/${lead.id}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    scored++;
                    
                    // Update the lead in currentLeads array
                    const idx = currentLeads.findIndex(l => l.id === lead.id);
                    if (idx !== -1 && data.lead) {
                        currentLeads[idx] = data.lead;
                    }
                    
                    if (data.failed) failed++;
                    
                    // Update progress and re-render table to show score immediately
                    updateProgressWithDetail(3, `Scoring leads...`, scored, total);
                    renderLeadsTable();
                    
                    // Update credits display in real-time
                    loadCredits();
                } else if (response.status === 402) {
                    // Out of credits
                    updateProgressWithDetail(3, `Out of credits! Scored ${scored}/${total}`, scored, total);
                    break;
                } else {
                    scored++;
                    failed++;
                    updateProgressWithDetail(3, `Scoring leads...`, scored, total);
                }
            } catch (error) {
                console.error(`Error scoring lead ${lead.id}:`, error);
                scored++;
                failed++;
                updateProgressWithDetail(3, `Scoring leads...`, scored, total);
            }
        }
        
        loadAnalytics();
        loadCredits();
        
        const successCount = scored - failed;
        if (failed > 0) {
            updateProgress(3, `Done! Scored ${successCount} leads (${failed} couldn't be analyzed)`);
        } else {
            updateProgress(3, `Campaign ready! Scored ${scored} leads.`);
        }
        
        setTimeout(() => {
            closeProgressModal();
        }, 2000);
    } else {
        updateProgress(3, 'Campaign ready! All leads scored.');
        setTimeout(() => {
            closeProgressModal();
        }, 2000);
    }
}

async function loadMoreLeads() {
    showStatus('leadsStatus', 'Loading more leads...', 'info');

    try {
        const response = await fetch('/api/load-more-leads', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (response.ok) {
            showStatus('leadsStatus', `Loaded ${data.count} more leads!`, 'success');
            currentLeads = [...currentLeads, ...data.leads];
            renderLeadsTable();
            loadAnalytics();
            
            const loadMoreBtn = document.getElementById('loadMoreBtn');
            if (data.campaign && data.campaign.has_more) {
                loadMoreBtn.style.display = 'inline-block';
            } else {
                loadMoreBtn.style.display = 'none';
            }
            
            setTimeout(() => showStatus('leadsStatus', '', ''), 3000);
        } else {
            showStatus('leadsStatus', `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('leadsStatus', `Error: ${error.message}`, 'error');
    }
}

let needsEmailFilterActive = false;

function renderTechPillsCompact(lead) {
    if (!lead.technographics || !lead.technographics.detected) {
        return '<span class="tech-pill tech-pill-grey">Not analysed</span>';
    }
    const t = lead.technographics;
    const pills = [];

    if (t.ssl === true) pills.push({text: 'SSL', cls: 'tech-pill-green'});
    else if (t.ssl === false) pills.push({text: 'No SSL', cls: 'tech-pill-red'});

    if (t.mobile_responsive === true) pills.push({text: 'Mobile', cls: 'tech-pill-green'});
    else if (t.mobile_responsive === false) pills.push({text: 'Not Mobile', cls: 'tech-pill-red'});

    if (t.cms && t.cms.name) {
        let cmsCls = 'tech-pill-green';
        if (t.cms.name.toLowerCase().includes('wordpress') && t.cms_version) {
            const major = parseInt(t.cms_version);
            if (!isNaN(major) && major < 6) cmsCls = 'tech-pill-amber';
        }
        pills.push({text: t.cms.name, cls: cmsCls});
    }

    const hasAnalytics = t.analytics && (t.analytics.google_analytics || t.analytics.meta_pixel || (t.analytics.other && t.analytics.other.length > 0));
    if (hasAnalytics) pills.push({text: 'Analytics', cls: 'tech-pill-green'});
    else if (t.analytics && !hasAnalytics) pills.push({text: 'No Analytics', cls: 'tech-pill-red'});

    return pills.slice(0, 4).map(p => `<span class="tech-pill ${p.cls}">${p.text}</span>`).join('');
}

function renderTechSectionFull(technographics) {
    if (!technographics || !technographics.detected) return '';
    const t = technographics;
    let html = '<div class="tech-section"><div class="tech-section-title">🔬 Technology Stack</div>';

    // Security & Infrastructure
    html += '<div class="tech-group"><div class="tech-group-label">Security & Infrastructure</div><div class="tech-pills-row">';
    html += t.ssl ? '<span class="tech-pill tech-pill-green">🔒 HTTPS</span>' : '<span class="tech-pill tech-pill-red">⚠️ No SSL</span>';
    html += t.mobile_responsive ? '<span class="tech-pill tech-pill-green">📱 Responsive</span>' : '<span class="tech-pill tech-pill-red">❌ Not Responsive</span>';
    html += t.favicon ? '<span class="tech-pill tech-pill-green">🎨 Favicon</span>' : '<span class="tech-pill tech-pill-red">❌ No Favicon</span>';
    html += t.cookie_consent ? '<span class="tech-pill tech-pill-green">🍪 Cookie Consent</span>' : '<span class="tech-pill tech-pill-amber">🍪 No Cookie Consent</span>';
    html += '</div></div>';

    // CMS & Frameworks
    if (t.cms && t.cms.name) {
        html += '<div class="tech-group"><div class="tech-group-label">CMS & Platform</div><div class="tech-pills-row">';
        let cmsCls = 'tech-pill-green';
        let cmsLabel = t.cms.name;
        if (t.cms.name.toLowerCase().includes('wordpress') && t.cms_version) {
            const major = parseInt(t.cms_version);
            if (!isNaN(major) && major < 6) cmsCls = 'tech-pill-amber';
            cmsLabel += ' ' + t.cms_version;
        } else if (t.cms_version) {
            cmsLabel += ' ' + t.cms_version;
        }
        html += `<span class="tech-pill ${cmsCls}">🏗️ ${cmsLabel}</span>`;
        if (t.cms.confidence) html += `<span class="tech-pill tech-pill-grey">${Math.round(t.cms.confidence * 100)}% confidence</span>`;
        html += '</div></div>';
    }

    // jQuery
    if (t.jquery && t.jquery.present) {
        html += '<div class="tech-group"><div class="tech-group-label">JavaScript Libraries</div><div class="tech-pills-row">';
        let jqCls = 'tech-pill-green';
        let jqLabel = 'jQuery';
        if (t.jquery.version) {
            const major = parseInt(t.jquery.version);
            if (!isNaN(major) && major < 3) jqCls = 'tech-pill-amber';
            jqLabel += ' ' + t.jquery.version;
        }
        html += `<span class="tech-pill ${jqCls}">⚡ ${jqLabel}</span>`;
        html += '</div></div>';
    }

    // Analytics
    html += '<div class="tech-group"><div class="tech-group-label">Analytics & Tracking</div><div class="tech-pills-row">';
    const hasAny = t.analytics && (t.analytics.google_analytics || t.analytics.meta_pixel || (t.analytics.other && t.analytics.other.length > 0));
    if (!hasAny) {
        html += '<span class="tech-pill tech-pill-red">❌ No Analytics</span>';
    } else {
        if (t.analytics.google_analytics) html += '<span class="tech-pill tech-pill-green">📊 Google Analytics</span>';
        if (t.analytics.meta_pixel) html += '<span class="tech-pill tech-pill-green">📊 Meta Pixel</span>';
        if (t.analytics.other && t.analytics.other.length > 0) {
            t.analytics.other.forEach(a => { html += `<span class="tech-pill tech-pill-green">📊 ${a}</span>`; });
        }
    }
    html += '</div></div>';

    // OG Tags
    if (t.og_tags) {
        html += '<div class="tech-group"><div class="tech-group-label">SEO & Open Graph</div><div class="tech-pills-row">';
        const bothOG = t.og_tags.has_og_title && t.og_tags.has_og_image;
        const anyOG = t.og_tags.has_og_title || t.og_tags.has_og_image;
        if (bothOG) {
            html += '<span class="tech-pill tech-pill-green">✅ OG Title</span><span class="tech-pill tech-pill-green">✅ OG Image</span>';
        } else if (anyOG) {
            html += t.og_tags.has_og_title ? '<span class="tech-pill tech-pill-green">✅ OG Title</span>' : '<span class="tech-pill tech-pill-amber">⚠️ No OG Title</span>';
            html += t.og_tags.has_og_image ? '<span class="tech-pill tech-pill-green">✅ OG Image</span>' : '<span class="tech-pill tech-pill-amber">⚠️ No OG Image</span>';
        } else {
            html += '<span class="tech-pill tech-pill-amber">⚠️ No OG Tags</span>';
        }
        html += '</div></div>';
    }

    // Page Bloat
    if (t.page_bloat) {
        html += '<div class="tech-group"><div class="tech-group-label">Page Resources</div><div class="tech-pills-row">';
        html += `<span class="tech-pill tech-pill-grey">📜 ${t.page_bloat.external_scripts || 0} scripts</span>`;
        html += `<span class="tech-pill tech-pill-grey">🎨 ${t.page_bloat.external_stylesheets || 0} stylesheets</span>`;
        html += `<span class="tech-pill tech-pill-grey">📦 ${t.page_bloat.total_external || 0} total external</span>`;
        html += '</div></div>';
    }

    // Social Links
    if (t.social_links) {
        const socialEntries = Object.entries(t.social_links).filter(([k, v]) => v);
        if (socialEntries.length > 0) {
            html += '<div class="tech-group"><div class="tech-group-label">Social Media</div><div class="tech-pills-row">';
            const icons = {facebook:'📘',instagram:'📷',linkedin:'💼',twitter:'🐦',youtube:'🎬',tiktok:'🎵'};
            socialEntries.forEach(([platform, url]) => {
                const icon = icons[platform] || '🔗';
                html += `<a href="${url}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;"><span class="tech-pill tech-pill-green">${icon} ${platform.charAt(0).toUpperCase()+platform.slice(1)}</span></a>`;
            });
            const count = socialEntries.length;
            if (count <= 2) {
                html += '<span class="tech-pill tech-pill-amber">⚠️ Limited social presence</span>';
            }
            html += '</div></div>';
        }
    }

    html += '</div>';
    return html;
}

function toggleSourceFilter() {
    sourceFilterActive = document.getElementById('sourceFilter').value;
    renderLeadsTable();
}

function renderLeadsTable() {
    const tbody = document.getElementById('leadsTableBody');
    
    let leadsToRender = currentLeads;
    if (needsEmailFilterActive) {
        leadsToRender = leadsToRender.filter(lead => !lead.email || lead.email === '');
    }
    if (sourceFilterActive !== 'all') {
        leadsToRender = leadsToRender.filter(lead => (lead.source || 'search') === sourceFilterActive);
    }
    
    // Apply sorting
    leadsToRender = getSortedLeads(leadsToRender);

    if (leadsToRender.length === 0) {
        tbody.innerHTML = '<tr><td colspan="16" class="no-data">No leads matching filter.</td></tr>';
        return;
    }
    
    // Update sort indicators in headers
    updateSortIndicators();
    
    // Update selection UI
    updateSelectionUI();

    tbody.innerHTML = leadsToRender.map(lead => `
        <tr onclick="selectLead('${lead.id}')" data-lead-id="${lead.id}" class="lead-row">
            <td onclick="event.stopPropagation()" style="text-align: center;">
                <input type="checkbox" class="lead-checkbox" data-lead-id="${lead.id}" 
                    ${selectedLeadIds.has(lead.id) ? 'checked' : ''} 
                    onclick="toggleLeadSelection('${lead.id}', this.checked)" />
            </td>
            <td>${lead.name}${renderSourceBadge(lead)}</td>
            <td class="editable" onclick="editContactName(event, '${lead.id}')">${lead.contact_name || 'Add contact...'}</td>
            <td>${lead.address}</td>
            <td class="editable" onclick="editPhone(event, '${lead.id}')">${lead.phone || 'Add phone...'}</td>
            <td>${lead.website ? `<a href="${lead.website.startsWith('http') ? lead.website : 'https://' + lead.website}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation();" style="color: #667eea;">View</a>` : 'N/A'}</td>
            <td class="editable" onclick="editEmail(event, '${lead.id}')">${lead.email || 'Add email...'}</td>
            <td>${renderEmailSource(lead.email_source)}</td>
            <td>${renderScoreWithImportStatus(lead)}</td>
            <td>${renderComponentScore(lead, 'website', 30)}</td>
            <td>${renderComponentScore(lead, 'presence', 30)}</td>
            <td>${renderComponentScore(lead, 'automation', 40)}</td>
            <td>${renderTechPillsCompact(lead)}</td>
            <td>${renderStageDropdown(lead.id, lead.stage)}</td>
            <td class="editable" onclick="editNotes(event, '${lead.id}')">${lead.notes || 'Add notes...'}</td>
            <td onclick="event.stopPropagation()">
                <button onclick="deleteLead('${lead.id}')" style="background: #ef4444; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 12px;">Delete</button>
            </td>
        </tr>
    `).join('');
}

function renderSourceBadge(lead) {
    const source = lead.source || 'search';
    if (source === 'import') {
        return ' <span class="lead-source-badge source-import">Imported</span>';
    }
    return '';
}

function renderScoreWithImportStatus(lead) {
    const importStatus = lead.import_status;
    if (importStatus === 'queued' || importStatus === 'scoring') {
        return '<span class="lead-import-status"><span class="spinner-small"></span> Scoring...</span>';
    }
    if (importStatus === 'unreachable') {
        return '<span style="color:#9ca3af;font-size:12px;">Unreachable</span>';
    }
    if (importStatus === 'pending_credits') {
        return '<span style="color:#f59e0b;font-size:12px;">Awaiting credits</span>';
    }
    return renderScore(lead.score, lead.id);
}

function renderEmailSource(source) {
    if (!source) return '-';
    
    const colors = {
        'website': '#3b82f6',
        'hunter': '#a855f7',
        'manual': '#64748b'
    };
    
    const color = colors[source] || '#64748b';
    return `<span style="background: ${color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; text-transform: uppercase;">${source}</span>`;
}

function handleWebsiteClick(event, url) {
    event.stopPropagation();
    
    // Ensure URL has protocol
    const fullUrl = url.startsWith('http') ? url : 'https://' + url;
    
    // Show options dialog
    const message = `Website: ${fullUrl}\n\nChoose an option:`;
    const choice = confirm(message + '\n\nOK = Copy URL to clipboard\nCancel = Open in new tab');
    
    if (choice) {
        // Copy to clipboard
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(fullUrl).then(() => {
                alert('✓ URL copied to clipboard! Paste it in Safari to open.');
            }).catch(() => {
                // Fallback - show URL to manually copy
                prompt('Copy this URL:', fullUrl);
            });
        } else {
            // Fallback - show URL to manually copy
            prompt('Copy this URL:', fullUrl);
        }
    } else {
        // Try to open in new tab
        window.open(fullUrl, '_blank', 'noopener,noreferrer');
    }
}

function toggleNeedsEmailFilter() {
    needsEmailFilterActive = document.getElementById('needsEmailFilter').checked;
    renderLeadsTable();
}

function toggleLeadSelection(leadId, isChecked) {
    if (isChecked) {
        selectedLeadIds.add(leadId);
    } else {
        selectedLeadIds.delete(leadId);
    }
    updateSelectionUI();
}

function toggleSelectAllLeads() {
    const selectAll = document.getElementById('selectAllLeads');
    const checkboxes = document.querySelectorAll('.lead-checkbox');
    
    if (selectAll.checked) {
        checkboxes.forEach(cb => {
            const leadId = cb.dataset.leadId;
            selectedLeadIds.add(leadId);
            cb.checked = true;
        });
    } else {
        selectedLeadIds.clear();
        checkboxes.forEach(cb => cb.checked = false);
    }
    updateSelectionUI();
}

function clearLeadSelection() {
    selectedLeadIds.clear();
    document.querySelectorAll('.lead-checkbox').forEach(cb => cb.checked = false);
    const selectAll = document.getElementById('selectAllLeads');
    if (selectAll) selectAll.checked = false;
    updateSelectionUI();
}

function updateSelectionUI() {
    const count = selectedLeadIds.size;
    const infoEl = document.getElementById('selectionInfo');
    const countEl = document.getElementById('selectedCount');
    const emailBtn = document.getElementById('emailSelectedBtn');
    const smsBtn = document.getElementById('smsSelectedBtn');
    
    if (count > 0) {
        infoEl.style.display = 'inline';
        countEl.textContent = count;
        if (emailBtn) emailBtn.style.display = 'inline-block';
        if (smsBtn) smsBtn.style.display = 'inline-block';
    } else {
        infoEl.style.display = 'none';
        if (emailBtn) emailBtn.style.display = 'none';
        if (smsBtn) smsBtn.style.display = 'none';
    }
    
    // Update select all checkbox state
    const selectAll = document.getElementById('selectAllLeads');
    const checkboxes = document.querySelectorAll('.lead-checkbox');
    if (selectAll && checkboxes.length > 0) {
        selectAll.checked = checkboxes.length === selectedLeadIds.size;
    }
}

function emailSelectedLeads() {
    if (selectedLeadIds.size === 0) {
        showNotification('Please select at least one lead first', 'warning');
        return;
    }
    showPage('email');
}

function smsSelectedLeads() {
    if (selectedLeadIds.size === 0) {
        showNotification('Please select at least one lead first', 'warning');
        return;
    }
    showPage('sms');
}

function getSelectedLeads() {
    return currentLeads.filter(lead => selectedLeadIds.has(lead.id));
}

function renderScore(score, leadId) {
    const lead = currentLeads.find(l => l.id === leadId);
    const status = lead ? lead.score_status : null;

    if (status === 'not_scored' || (!status && (score === null || score === undefined || score === 0) && (!lead || !lead.score_reasoning))) {
        return '<span class="score-badge score-not-scored" title="Not scored yet">-</span>';
    }

    if (status === 'bot_protected') {
        return `<span class="score-badge score-bot-protected" onclick="event.stopPropagation(); showScoreBreakdown('${leadId}')" style="cursor: pointer;" title="${lead.score_fail_reason || 'Website has advanced bot protection'}">Bot Protected</span>` +
            `<button class="retry-score-btn" onclick="event.stopPropagation(); retrySingleScore('${leadId}')" title="Retry scoring">&#x21bb;</button>`;
    }

    if (status === 'failed') {
        return `<span class="score-badge score-failed" onclick="event.stopPropagation(); showScoreBreakdown('${leadId}')" style="cursor: pointer;" title="${lead.score_fail_reason || 'Scoring failed'}">Failed</span>` +
            `<button class="retry-score-btn" onclick="event.stopPropagation(); retrySingleScore('${leadId}')" title="Retry scoring">&#x21bb;</button>`;
    }

    if (lead && lead.score_reasoning) {
        let reasoning = lead.score_reasoning;
        if (typeof reasoning === 'string') {
            try { reasoning = JSON.parse(reasoning); } catch (e) { reasoning = {}; }
        }
        if (reasoning.bot_blocked && status !== 'scored') {
            return `<span class="score-badge score-bot-protected" onclick="event.stopPropagation(); showScoreBreakdown('${leadId}')" style="cursor: pointer;" title="Website has advanced bot protection">Bot Protected</span>` +
                `<button class="retry-score-btn" onclick="event.stopPropagation(); retrySingleScore('${leadId}')" title="Retry scoring">&#x21bb;</button>`;
        }
    }

    let className = 'score-low';
    if (score >= 80) className = 'score-excellent';
    else if (score >= 50) className = 'score-high';
    else if (score >= 30) className = 'score-medium';

    return `<span class="score-badge ${className}" onclick="event.stopPropagation(); showScoreBreakdown('${leadId}')" style="cursor: pointer;" title="Click to see score breakdown">${score}</span>`;
}

async function retrySingleScore(leadId) {
    const lead = currentLeads.find(l => l.id === leadId);
    if (!lead) return;
    
    const row = document.querySelector(`tr[data-lead-id="${leadId}"]`);
    if (row) {
        const scoreCell = row.querySelectorAll('td')[8];
        if (scoreCell) scoreCell.innerHTML = '<span class="score-badge score-not-scored" style="animation: pulse 1s infinite;">Scoring...</span>';
    }
    
    try {
        const response = await fetch(`/api/score-lead/${leadId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await safeJsonParse(response);
        if (response.ok && data.lead) {
            const idx = currentLeads.findIndex(l => l.id === leadId);
            if (idx !== -1) currentLeads[idx] = data.lead;
            renderLeadsTable();
            showStatus('searchStatus', `Rescored ${lead.name}: ${data.lead.score}/100`, 'success');
        } else {
            showStatus('searchStatus', data.detail || 'Retry scoring failed', 'error');
            renderLeadsTable();
        }
    } catch (err) {
        showStatus('searchStatus', 'Error retrying score', 'error');
        renderLeadsTable();
    }
}

function renderComponentScore(lead, component, maxScore) {
    if (!lead.score_reasoning || lead.score_status === 'not_scored' || lead.score_status === 'failed' || lead.score_status === 'bot_protected') return '-';
    
    const reasoning = lead.score_reasoning;
    let score = 0;
    
    if (component === 'website' && reasoning.website_quality) {
        score = reasoning.website_quality.score || 0;
    } else if (component === 'presence' && reasoning.digital_presence) {
        score = reasoning.digital_presence.score || 0;
    } else if (component === 'automation' && reasoning.automation_opportunity) {
        score = reasoning.automation_opportunity.score || 0;
    }
    
    // Calculate percentage for color coding
    const percentage = (score / maxScore) * 100;
    
    let className = 'score-component-low';
    if (percentage >= 70) className = 'score-component-high';
    else if (percentage >= 50) className = 'score-component-medium';
    
    return `<span class="score-component ${className}" data-score="${score}">${score}/${maxScore}</span>`;
}

function renderStageDropdown(leadId, currentStage) {
    const stages = ['New', 'Contacted', 'Replied', 'Meeting', 'Closed Won', 'Closed Lost'];
    const options = stages.map(stage => 
        `<option value="${stage}" ${stage === currentStage ? 'selected' : ''}>${stage}</option>`
    ).join('');

    return `<select onchange="updateStage('${leadId}', this.value)" onclick="event.stopPropagation()" style="background: rgba(255,255,255,0.1); color: #e0e0e0; border: 1px solid rgba(255,255,255,0.2); padding: 5px; border-radius: 4px;">${options}</select>`;
}

function selectLead(leadId) {
    document.getElementById('selectedLeadId').value = leadId;
    const lead = currentLeads.find(l => l.id === leadId);
    if (lead) {
        // Update the selected lead display
        const selectedDisplay = document.getElementById('selectedLeadDisplay');
        const noLeadHint = document.getElementById('noLeadSelected');
        if (selectedDisplay) {
            selectedDisplay.innerHTML = `<strong>${lead.name}</strong> ${lead.email ? `(${lead.email})` : '<span style="color: #ef4444;">(no email - add one first)</span>'}`;
            selectedDisplay.style.display = 'block';
        }
        if (noLeadHint) {
            noLeadHint.style.display = 'none';
        }
        // Highlight selected row
        document.querySelectorAll('#leadsTableBody tr').forEach(row => row.classList.remove('selected-row'));
        const selectedRow = document.querySelector(`tr[data-lead-id="${leadId}"]`);
        if (selectedRow) selectedRow.classList.add('selected-row');
        
        showStatus('leadsStatus', `Selected: ${lead.name}`, 'info');
    }
}

function editEmail(event, leadId) {
    event.stopPropagation();
    const lead = currentLeads.find(l => String(l.id) === String(leadId));
    if (!lead) return;
    showInlineEditModal('Email Address', lead.email || '', 'email', async (value) => {
        await updateLead(leadId, { email: value });
    });
}

function editPhone(event, leadId) {
    event.stopPropagation();
    const lead = currentLeads.find(l => String(l.id) === String(leadId));
    if (!lead) return;
    showInlineEditModal('Phone Number', lead.phone || '', 'tel', async (value) => {
        await updateLead(leadId, { phone: value });
    });
}

function editContactName(event, leadId) {
    event.stopPropagation();
    const lead = currentLeads.find(l => String(l.id) === String(leadId));
    if (!lead) return;
    showInlineEditModal('Contact Name', lead.contact_name || '', 'text', async (value) => {
        await updateLead(leadId, { contact_name: value });
    });
}

function editNotes(event, leadId) {
    event.stopPropagation();
    const lead = currentLeads.find(l => String(l.id) === String(leadId));
    if (!lead) return;
    showInlineEditModal('Notes', lead.notes || '', 'textarea', async (value) => {
        await updateLead(leadId, { notes: value });
    });
}

function showInlineEditModal(title, currentValue, inputType, onSave) {
    const existingModal = document.getElementById('inlineEditModal');
    if (existingModal) existingModal.remove();
    
    const overlay = document.createElement('div');
    overlay.id = 'inlineEditModal';
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;justify-content:center;align-items:center;z-index:10000;';
    
    const modal = document.createElement('div');
    modal.style.cssText = 'background:white;border-radius:12px;padding:24px;max-width:400px;width:90%;box-shadow:0 10px 40px rgba(0,0,0,0.2);';
    
    const inputHtml = inputType === 'textarea' 
        ? `<textarea id="inlineEditInput" rows="4" style="width:100%;padding:12px;border:1px solid #d1d5db;border-radius:8px;font-size:14px;font-family:inherit;resize:vertical;">${currentValue}</textarea>`
        : `<input type="${inputType}" id="inlineEditInput" value="${currentValue.replace(/"/g, '&quot;')}" style="width:100%;padding:12px;border:1px solid #d1d5db;border-radius:8px;font-size:14px;" />`;
    
    modal.innerHTML = `
        <h3 style="margin:0 0 16px 0;color:#333;font-size:18px;">Edit ${title}</h3>
        ${inputHtml}
        <div style="display:flex;gap:12px;margin-top:16px;justify-content:flex-end;">
            <button id="inlineEditCancel" style="padding:10px 20px;border:1px solid #d1d5db;background:white;border-radius:8px;cursor:pointer;font-size:14px;">Cancel</button>
            <button id="inlineEditSave" style="padding:10px 20px;border:none;background:linear-gradient(135deg,#8b5cf6 0%,#a855f7 100%);color:white;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500;">Save</button>
        </div>
    `;
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    const input = document.getElementById('inlineEditInput');
    input.focus();
    if (inputType !== 'textarea') {
        input.select();
    }
    
    const closeModal = () => overlay.remove();
    
    document.getElementById('inlineEditCancel').onclick = closeModal;
    overlay.onclick = (e) => { if (e.target === overlay) closeModal(); };
    
    document.getElementById('inlineEditSave').onclick = async () => {
        const newValue = input.value.trim();
        closeModal();
        await onSave(newValue);
    };
    
    input.onkeydown = async (e) => {
        if (e.key === 'Enter' && inputType !== 'textarea') {
            e.preventDefault();
            const newValue = input.value.trim();
            closeModal();
            await onSave(newValue);
        } else if (e.key === 'Escape') {
            closeModal();
        }
    };
}

async function updateStage(leadId, newStage) {
    await updateLead(leadId, { stage: newStage });
}

async function updateLead(leadId, updates) {
    try {
        const response = await fetch(`/api/leads/${leadId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });

        const data = await response.json();
        
        if (response.ok) {
            showStatus('leadsStatus', '✓ Lead updated successfully', 'success');
            
            // Update local data instantly instead of full reload
            const leadIndex = currentLeads.findIndex(l => String(l.id) === String(leadId));
            if (leadIndex !== -1) {
                Object.assign(currentLeads[leadIndex], updates);
                renderLeadsTable();
                
                // Also update lead details panel if this lead is currently displayed
                const selectedLeadIdElement = document.getElementById('selectedLeadId');
                if (selectedLeadIdElement && String(selectedLeadIdElement.value) === String(leadId)) {
                    displayLeadDetails(currentLeads[leadIndex]);
                }
            }
            
            setTimeout(() => showStatus('leadsStatus', '', ''), 3000);
        } else {
            showStatus('leadsStatus', `Error: ${data.detail || 'Failed to update lead'}`, 'error');
            console.error('Update failed:', data);
        }
    } catch (error) {
        showStatus('leadsStatus', `Error: ${error.message}`, 'error');
        console.error('Error updating lead:', error);
    }
}

async function deleteLead(leadId) {
    const lead = currentLeads.find(l => l.id === leadId);
    const leadName = lead ? lead.name : 'this lead';
    
    if (!confirm(`Are you sure you want to delete ${leadName}? This action cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/leads/${leadId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            showStatus('leadsStatus', `✓ ${leadName} deleted successfully`, 'success');
            await loadLeads();
            await loadAnalytics();
            setTimeout(() => showStatus('leadsStatus', '', ''), 3000);
        } else {
            showStatus('leadsStatus', `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('leadsStatus', `Error deleting lead: ${error.message}`, 'error');
    }
}

async function enrichFromWebsite() {
    try {
        showStatus('leadsStatus', 'Enriching emails from websites...', 'info');
        
        const leadsNeedingEmail = currentLeads.filter(lead => !lead.email && lead.website);
        const leadIds = leadsNeedingEmail.map(l => l.id);
        
        const response = await fetch('/api/enrich-from-website', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lead_ids: leadIds.length > 0 ? leadIds : undefined })
        });

        const data = await response.json();

        if (response.ok) {
            showStatus('leadsStatus', `✓ Found emails for ${data.updated} leads from their websites!`, 'success');
            await loadLeads();
            setTimeout(() => showStatus('leadsStatus', '', ''), 5000);
        } else {
            showStatus('leadsStatus', `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('leadsStatus', `Error: ${error.message}`, 'error');
    }
}

async function enrichFromHunter() {
    if (!checkAPIKeys('hunter')) {
        showMissingKeysModal('hunter', 'Hunter.io email enrichment');
        return;
    }

    try {
        showStatus('leadsStatus', 'Enriching emails via Hunter.io...', 'info');
        
        const response = await fetch('/api/enrich-from-hunter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ max_per_domain: 3 })
        });

        const data = await response.json();

        if (response.ok) {
            showStatus('leadsStatus', `✓ Found emails for ${data.updated} leads via Hunter.io!`, 'success');
            await loadLeads();
            setTimeout(() => showStatus('leadsStatus', '', ''), 5000);
        } else {
            showStatus('leadsStatus', `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('leadsStatus', `Error: ${error.message}`, 'error');
    }
}

let emailTemplates = [];

async function loadEmailTemplates() {
    try {
        const response = await fetch('/api/email-templates');
        if (response.ok) {
            const data = await response.json();
            emailTemplates = data.templates || [];
            renderTemplateDropdown();
        }
    } catch (error) {
        console.error('Error loading email templates:', error);
    }
}

function renderTemplateDropdown() {
    const select = document.getElementById('templateSelect');
    if (!select) return;
    
    select.innerHTML = '<option value="">-- Select a template --</option>';
    emailTemplates.forEach(t => {
        const option = document.createElement('option');
        option.value = t.id;
        option.textContent = t.name;
        select.appendChild(option);
    });
}

function loadSelectedTemplate() {
    const select = document.getElementById('templateSelect');
    const templateId = select.value;
    
    if (!templateId) return;
    
    const template = emailTemplates.find(t => t.id == templateId);
    if (template) {
        document.getElementById('subjectTemplate').value = template.subject || '';
        document.getElementById('bodyTemplate').value = template.body || '';
        showStatus('templateStatus', `✓ Loaded: ${template.name}`, 'success');
        setTimeout(() => showStatus('templateStatus', '', ''), 2000);
    }
}

async function saveCurrentTemplate() {
    const subject = document.getElementById('subjectTemplate').value;
    const body = document.getElementById('bodyTemplate').value;
    
    if (!subject && !body) {
        showStatus('templateStatus', '✗ Please enter a subject or body first', 'error');
        return;
    }
    
    const name = prompt('Enter a name for this template:', '');
    if (!name) return;
    
    try {
        const response = await fetch('/api/email-templates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, subject, body })
        });
        
        if (response.ok) {
            showStatus('templateStatus', `✓ Template "${name}" saved!`, 'success');
            await loadEmailTemplates();
            setTimeout(() => showStatus('templateStatus', '', ''), 3000);
        } else {
            const error = await response.json();
            showStatus('templateStatus', `✗ ${error.detail || 'Failed to save'}`, 'error');
        }
    } catch (error) {
        showStatus('templateStatus', `✗ Error: ${error.message}`, 'error');
    }
}

async function deleteSelectedTemplate() {
    const select = document.getElementById('templateSelect');
    const templateId = select.value;
    
    if (!templateId) {
        showStatus('templateStatus', '✗ Please select a template first', 'error');
        return;
    }
    
    const template = emailTemplates.find(t => t.id == templateId);
    if (!confirm(`Delete template "${template?.name}"? This cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/email-templates/${templateId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showStatus('templateStatus', '✓ Template deleted', 'success');
            await loadEmailTemplates();
            setTimeout(() => showStatus('templateStatus', '', ''), 3000);
        } else {
            const error = await response.json();
            showStatus('templateStatus', `✗ ${error.detail || 'Failed to delete'}`, 'error');
        }
    } catch (error) {
        showStatus('templateStatus', `✗ Error: ${error.message}`, 'error');
    }
}

async function previewEmails() {
    const subjectTemplate = document.getElementById('subjectTemplate').value;
    const bodyTemplate = document.getElementById('bodyTemplate').value;

    if (!subjectTemplate || !bodyTemplate) {
        alert('Please enter both subject and body templates');
        return;
    }

    try {
        const response = await fetch('/api/preview-emails', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subject_template: subjectTemplate, body_template: bodyTemplate })
        });

        const data = await response.json();

        if (response.ok) {
            renderEmailPreviews(data.previews);
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

function renderEmailPreviews(previews) {
    const container = document.getElementById('emailPreview');

    if (previews.length === 0) {
        container.innerHTML = '<p class="info-text">No leads to preview. Search for leads first.</p>';
        return;
    }

    container.innerHTML = '<div class="email-preview">' +
        '<h3>Preview (First 5 Leads)</h3>' +
        previews.map(p => `
            <div class="email-item">
                <h4>${p.lead_name}</h4>
                <div class="subject">Subject: ${p.subject}</div>
                <div class="body">${p.body}</div>
            </div>
        `).join('') +
        '</div>';
}

async function generatePersonalized() {
    const leadId = document.getElementById('selectedLeadId').value;
    const basePitch = document.getElementById('basePitch').value;
    const previewContainer = document.getElementById('personalizedEmailPreview');
    const generateBtn = document.querySelector('[onclick="generatePersonalized()"]');

    if (!leadId) {
        showToast('Please select a lead from the Leads table first by clicking on a row', 'error');
        return;
    }

    if (!basePitch) {
        showToast('Please enter your base pitch describing your services', 'error');
        return;
    }

    if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.dataset.originalText = generateBtn.textContent;
        generateBtn.textContent = 'Generating...';
    }

    previewContainer.innerHTML = `
        <div class="email-preview" style="text-align: center; padding: 30px;">
            <div style="color: #8b5cf6; font-size: 18px;">
                <div class="spinner" style="display: inline-block; width: 24px; height: 24px; border: 3px solid #e5e7eb; border-top: 3px solid #8b5cf6; border-radius: 50%; animation: spin 1s linear infinite; vertical-align: middle; margin-right: 10px;"></div>
                Generating AI email...
            </div>
            <p style="color: #666; margin-top: 10px;">This may take a few seconds</p>
        </div>
    `;

    saveBasePitch(basePitch);

    try {
        const response = await fetch('/api/generate-personalized', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lead_id: leadId, base_pitch: basePitch })
        });

        const data = await response.json();

        if (response.ok) {
            renderPersonalizedEmail(data);
            showToast('AI email generated successfully!', 'success');
        } else {
            previewContainer.innerHTML = '';
            showToast(data.detail || 'Failed to generate email. Please try again.', 'error');
        }
    } catch (error) {
        previewContainer.innerHTML = '';
        showToast('Network error: Could not reach the server. Please try again.', 'error');
    } finally {
        if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.textContent = generateBtn.dataset.originalText || 'Generate AI Email';
        }
    }
}

// Auto-save base pitch silently
async function saveBasePitch(pitch) {
    try {
        await fetch('/api/email-signature', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ base_pitch: pitch })
        });
    } catch (error) {
        console.error('Error saving base pitch:', error);
    }
}

async function renderPersonalizedEmail(data) {
    const container = document.getElementById('personalizedEmailPreview');
    
    // Fetch signature
    let signatureHtml = '';
    try {
        const sigResponse = await fetch('/api/email-signature');
        if (sigResponse.ok) {
            const sigData = await sigResponse.json();
            signatureHtml = buildSignatureHtml(sigData);
        }
    } catch (e) {
        console.error('Error fetching signature:', e);
    }
    
    container.innerHTML = `
        <div class="email-preview">
            <h3>AI-Generated Email for ${data.lead_name}</h3>
            <div class="email-item">
                <div class="subject">Subject: ${data.subject}</div>
                <div class="body">${data.body}${signatureHtml ? '<br><br>' + signatureHtml : ''}</div>
            </div>
            <p class="info-text">You can edit the templates above and use this as a guide for your outreach.</p>
        </div>
    `;
}

function buildSignatureHtml(sigData) {
    if (!sigData) return '';
    
    if (sigData.use_custom && sigData.custom_signature) {
        return sigData.custom_signature.replace(/\n/g, '<br>');
    }
    
    // Build standard signature
    let parts = [];
    if (sigData.full_name) parts.push(`<strong>${sigData.full_name}</strong>`);
    if (sigData.position) parts.push(sigData.position);
    if (sigData.company_name) parts.push(sigData.company_name);
    if (sigData.phone) parts.push(sigData.phone);
    if (sigData.website) parts.push(`<a href="${sigData.website}" style="color: #8b5cf6;">${sigData.website}</a>`);
    if (sigData.disclaimer) parts.push(`<small style="color: #888;">${sigData.disclaimer}</small>`);
    
    if (parts.length === 0) return '';
    
    return '<div style="margin-top: 20px; padding-top: 10px; border-top: 1px solid #e5e7eb; color: #666;">' + parts.join('<br>') + '</div>';
}

// Preview email for selected lead using templates
function previewSelectedLeadEmail() {
    const leadId = document.getElementById('selectedLeadId').value;
    const subjectTemplate = document.getElementById('subjectTemplate').value;
    const bodyTemplate = document.getElementById('bodyTemplate').value;
    const statusEl = document.getElementById('selectedEmailStatus');
    
    if (!leadId) {
        alert('Please select a lead from the Leads table first');
        return;
    }
    
    if (!subjectTemplate || !bodyTemplate) {
        alert('Please fill in the subject and body templates');
        return;
    }
    
    // Find the selected lead
    const lead = currentLeads.find(l => l.id === leadId);
    if (!lead) {
        alert('Selected lead not found. Please refresh and try again.');
        return;
    }
    
    if (!lead.email) {
        alert('This lead does not have an email address. Please enrich the lead first or add an email manually.');
        return;
    }
    
    // Parse location for city
    const city = lead.address ? lead.address.split(',')[0].trim() : 'your area';
    
    // Apply template variables
    const subject = subjectTemplate
        .replace(/\{\{business_name\}\}/g, lead.name)
        .replace(/\{\{city\}\}/g, city)
        .replace(/\{\{website\}\}/g, lead.website || '')
        .replace(/\{\{email\}\}/g, lead.email);
        
    const body = bodyTemplate
        .replace(/\{\{business_name\}\}/g, lead.name)
        .replace(/\{\{city\}\}/g, city)
        .replace(/\{\{website\}\}/g, lead.website || '')
        .replace(/\{\{email\}\}/g, lead.email);
    
    // Show preview
    const container = document.getElementById('personalizedEmailPreview');
    container.innerHTML = `
        <div class="email-preview">
            <h3>Email Preview for ${lead.name}</h3>
            <div class="email-item">
                <div class="to" style="color: #666; margin-bottom: 8px;"><strong>To:</strong> ${lead.email}</div>
                <div class="subject">Subject: ${subject}</div>
                <div class="body">${body.replace(/\n/g, '<br>')}</div>
            </div>
        </div>
    `;
    statusEl.innerHTML = '';
}

// Send email to selected lead
async function sendSelectedLeadEmail() {
    let leadId = document.getElementById('selectedLeadId').value;
    const subjectTemplate = document.getElementById('subjectTemplate').value;
    const bodyTemplate = document.getElementById('bodyTemplate').value;
    const includeReport = document.getElementById('includeScoreReport')?.checked || false;
    const attachPdf = document.getElementById('attachPdfReport')?.checked || false;
    const statusEl = document.getElementById('selectedEmailStatus');
    
    // Check for checkbox selection first, then fall back to row highlight
    if (selectedLeadIds.size === 1) {
        leadId = Array.from(selectedLeadIds)[0];
    } else if (selectedLeadIds.size > 1) {
        alert('Please select only one lead for single email, or use "Send to All" for bulk emails');
        return;
    }
    
    if (!leadId) {
        alert('Please select a lead by checking the checkbox or clicking on a row');
        return;
    }
    
    if (!subjectTemplate || !bodyTemplate) {
        alert('Please fill in the subject and body templates');
        return;
    }
    
    // Find the selected lead
    const lead = currentLeads.find(l => String(l.id) === String(leadId));
    if (!lead) {
        alert('Selected lead not found. Please refresh and try again.');
        return;
    }
    
    if (!lead.email) {
        alert('This lead does not have an email address. Please enrich the lead first or add an email manually.');
        return;
    }
    
    // Confirm before sending
    if (!confirm(`Send email to ${lead.name} (${lead.email})?`)) {
        return;
    }
    
    statusEl.innerHTML = '<span style="color: #8b5cf6;">Sending email...</span>';
    
    try {
        const response = await fetch('/api/send-single-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lead_id: leadId,
                subject_template: subjectTemplate,
                body_template: bodyTemplate,
                include_score_report: includeReport,
                attach_pdf_report: attachPdf
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusEl.innerHTML = `<span style="color: #10b981;">✓ Email sent successfully to ${lead.email}</span>`;
            loadCredits(); // Refresh credits
        } else {
            statusEl.innerHTML = `<span style="color: #ef4444;">✗ ${data.detail || 'Failed to send email'}</span>`;
        }
    } catch (error) {
        statusEl.innerHTML = `<span style="color: #ef4444;">✗ Error: ${error.message}</span>`;
    }
}

async function sendEmails() {
    const subjectTemplate = document.getElementById('subjectTemplate').value;
    const bodyTemplate = document.getElementById('bodyTemplate').value;
    const minScore = document.getElementById('minScore').value;
    const stageFilter = document.getElementById('stageFilter').value;
    const includeScoreReport = document.getElementById('includeScoreReport').checked;
    const attachPdfReport = document.getElementById('attachPdfReport')?.checked || false;

    if (!subjectTemplate || !bodyTemplate) {
        alert('Please enter both subject and body templates');
        return;
    }

    const selectedCount = selectedLeadIds.size;
    const confirmMsg = selectedCount > 0 
        ? `Are you sure you want to send emails to ${selectedCount} selected leads?`
        : 'Are you sure you want to send emails? This will send to all matching leads with email addresses.';
    
    const confirmed = confirm(confirmMsg);
    if (!confirmed) return;

    showLoadingOverlay('Sending Emails', 'Delivering messages to your leads...');
    showStatus('sendStatus', 'Sending emails...', 'info');

    try {
        const payload = {
            subject_template: subjectTemplate,
            body_template: bodyTemplate,
            include_score_report: includeScoreReport,
            attach_pdf_report: attachPdfReport
        };

        if (selectedCount > 0) {
            payload.lead_ids = Array.from(selectedLeadIds);
        } else {
            if (minScore) payload.only_scored_above = parseInt(minScore);
            if (stageFilter) payload.stage_filter = stageFilter;
        }

        const response = await fetch('/api/send-emails', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await safeJsonParse(response);

        if (response.ok) {
            let message = `Successfully sent ${data.sent} emails. Skipped ${data.skipped} leads.`;
            if (data.errors.length > 0) {
                message += ` ${data.errors.length} errors occurred.`;
            }
            showStatus('sendStatus', message, data.errors.length > 0 ? 'error' : 'success');
            if (selectedCount > 0) clearLeadSelection();
            loadLeads();
            loadAnalytics();
        } else {
            showStatus('sendStatus', `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('sendStatus', `Error: ${error.message}`, 'error');
    } finally {
        hideLoadingOverlay();
    }
}

async function exportCSV() {
    try {
        const response = await fetch('/api/export');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'leads.csv';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        alert(`Error exporting CSV: ${error.message}`);
    }
}

async function loadAnalytics() {
    try {
        const response = await fetch('/api/analytics');
        const data = await response.json();

        if (response.ok) {
            const totalLeads = data.total_leads || 0;
            const onboardingCard = document.getElementById('onboardingCard');
            const dashboardContent = document.getElementById('dashboardContent');
            
            if (totalLeads === 0 && onboardingCard && dashboardContent) {
                onboardingCard.style.display = 'block';
                dashboardContent.style.display = 'none';
            } else if (onboardingCard && dashboardContent) {
                onboardingCard.style.display = 'none';
                dashboardContent.style.display = 'block';
            }
            
            document.getElementById('totalLeads').textContent = totalLeads;
            document.getElementById('totalCampaigns').textContent = data.total_campaigns || 0;
            document.getElementById('highOpportunity').textContent = data.high_opportunity_leads;
            document.getElementById('emailsSent').textContent = data.emails_sent;
            document.getElementById('smsSent').textContent = data.sms_sent || 0;
            document.getElementById('dealsInProgress').textContent = data.deals_in_progress;

            const stages = data.by_stage;
            document.getElementById('stageNew').textContent = stages['New'] || 0;
            document.getElementById('stageContacted').textContent = stages['Contacted'] || 0;
            document.getElementById('stageReplied').textContent = stages['Replied'] || 0;
            document.getElementById('stageMeeting').textContent = stages['Meeting'] || 0;
            document.getElementById('stageClosedWon').textContent = stages['Closed Won'] || 0;
            document.getElementById('stageClosedLost').textContent = stages['Closed Lost'] || 0;
        }
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

function showStatus(elementId, message, type) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = 'status-text status-' + type;
}

function showLoadingOverlay(message, subtext) {
    let overlay = document.getElementById('loadingOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'loading-overlay';
        document.body.appendChild(overlay);
    }
    overlay.innerHTML = `
        <div class="loading-spinner"></div>
        <div class="loading-text">${message || 'Processing...'}</div>
        ${subtext ? '<div class="loading-subtext">' + subtext + '</div>' : ''}
        <div class="progress-container" style="width: 200px; margin-top: 16px;">
            <div class="progress-bar indeterminate"></div>
        </div>
    `;
    overlay.style.display = 'flex';
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

async function safeJsonParse(response) {
    const text = await response.text();
    try {
        return JSON.parse(text);
    } catch (e) {
        console.error('Failed to parse JSON:', text.substring(0, 200));
        throw new Error('Server returned an invalid response. Please try again.');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    checkResetToken();
    loadCampaigns();
    loadLeads();
    loadAnalytics();
    loadBasePitch();
    initHeroCardAnimation();
});

// Hero card scroll animation
function initHeroCardAnimation() {
    const heroCard = document.querySelector('.hero-card');
    if (!heroCard) return;
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.3
    });
    
    observer.observe(heroCard);
}

// Load saved base pitch on page load
async function loadBasePitch() {
    try {
        const response = await fetch('/api/email-signature');
        if (response.ok) {
            const data = await response.json();
            const pitchField = document.getElementById('basePitch');
            if (pitchField && data.base_pitch) {
                pitchField.value = data.base_pitch;
            }
        }
    } catch (error) {
        console.error('Error loading base pitch:', error);
    }
}

async function previewSMS() {
    const template = document.getElementById('smsTemplate').value;
    const previewContainer = document.getElementById('smsPreview');
    
    if (!template) {
        showStatus('smsStatus', 'Please enter an SMS message template', 'error');
        return;
    }
    
    if (!previewContainer) {
        showStatus('smsStatus', 'Preview container not found', 'error');
        return;
    }
    
    previewContainer.innerHTML = '<div class="loading-indicator"><div class="spinner"></div> Loading previews...</div>';
    showStatus('smsStatus', 'Generating SMS previews...', 'info');
    
    try {
        const response = await fetch('/api/preview-sms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ message_template: template })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || `Server error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.previews && data.previews.length > 0) {
            const previewHTML = data.previews.map(p => `
                <div class="preview-item">
                    <strong>${p.lead_name}</strong> (${p.phone})<br/>
                    <div class="preview-sms">${p.message}</div>
                </div>
            `).join('');
            
            previewContainer.innerHTML = previewHTML;
            showStatus('smsStatus', `Previewing ${data.count} SMS messages`, 'success');
        } else {
            previewContainer.innerHTML = '<p>No leads with phone numbers found.</p>';
            showStatus('smsStatus', 'No eligible leads found', 'warning');
        }
    } catch (error) {
        console.error('SMS preview error:', error);
        previewContainer.innerHTML = '';
        showStatus('smsStatus', `Error: ${error.message}`, 'error');
    }
}

async function sendSMS() {
    if (!checkAPIKeys('twilio')) {
        showMissingKeysModal('twilio', 'SMS sending');
        return;
    }

    const template = document.getElementById('smsTemplate').value;
    const minScore = parseInt(document.getElementById('smsMinScore').value) || null;
    const stageFilter = document.getElementById('smsStageFilter').value || null;
    
    if (!template) {
        showStatus('smsStatus', 'Please enter an SMS message template', 'error');
        return;
    }
    
    const selectedCount = selectedLeadIds.size;
    const confirmMsg = selectedCount > 0 
        ? `Are you sure you want to send SMS to ${selectedCount} selected leads?`
        : 'Are you sure you want to send SMS messages? This will send to all leads with phone numbers.';
    
    if (!confirm(confirmMsg)) {
        return;
    }
    
    showStatus('smsStatus', 'Sending SMS messages...', 'info');
    
    try {
        const payload = {
            message_template: template
        };
        
        if (selectedCount > 0) {
            payload.lead_ids = Array.from(selectedLeadIds);
        } else {
            payload.only_scored_above = minScore;
            payload.stage_filter = stageFilter;
        }
        
        const response = await fetch('/api/send-sms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            let message = `Sent ${data.sent} SMS messages.`;
            if (data.skipped > 0) message += ` Skipped ${data.skipped} leads.`;
            if (data.errors.length > 0) message += ` ${data.errors.length} errors occurred.`;
            
            showStatus('smsStatus', message, data.errors.length > 0 ? 'warning' : 'success');
            if (selectedCount > 0) clearLeadSelection();
            loadAnalytics();
        } else {
            showStatus('smsStatus', `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('smsStatus', `Error: ${error.message}`, 'error');
    }
}

document.getElementById('smsTemplate')?.addEventListener('input', function() {
    const count = this.value.length;
    document.getElementById('smsCharCount').textContent = count;
});

showPage('dashboard');

let currentTutorialStep = 1;
const totalTutorialSteps = 5;

function showTutorialModal() {
    document.getElementById('tutorialModal').style.display = 'flex';
    currentTutorialStep = 1;
    updateTutorialStep();
}

function hideTutorialModal() {
    document.getElementById('tutorialModal').style.display = 'none';
}

function updateTutorialStep() {
    document.querySelectorAll('.tutorial-step').forEach(step => {
        step.classList.remove('active');
    });
    
    const currentStep = document.querySelector(`.tutorial-step[data-step="${currentTutorialStep}"]`);
    if (currentStep) {
        currentStep.classList.add('active');
    }
    
    document.getElementById('tutorialProgressText').textContent = `Step ${currentTutorialStep} of ${totalTutorialSteps}`;
    
    const prevBtn = document.getElementById('tutorialPrevBtn');
    const nextBtn = document.getElementById('tutorialNextBtn');
    
    prevBtn.disabled = currentTutorialStep === 1;
    
    if (currentTutorialStep === totalTutorialSteps) {
        nextBtn.textContent = 'Get Started';
        nextBtn.onclick = completeTutorial;
    } else {
        nextBtn.textContent = 'Next';
        nextBtn.onclick = nextTutorialStep;
    }
}

function nextTutorialStep() {
    if (currentTutorialStep < totalTutorialSteps) {
        currentTutorialStep++;
        updateTutorialStep();
    }
}

function previousTutorialStep() {
    if (currentTutorialStep > 1) {
        currentTutorialStep--;
        updateTutorialStep();
    }
}

async function completeTutorial() {
    try {
        await fetch('/api/user/tutorial-completed', {
            method: 'PUT'
        });
        
        if (currentUser && currentUser.user) {
            currentUser.user.completed_tutorial = true;
        }
        
        hideTutorialModal();
    } catch (error) {
        console.error('Error completing tutorial:', error);
        hideTutorialModal();
    }
}

async function skipTutorial() {
    const confirmed = confirm('Are you sure you want to skip the tutorial? You can always access help from the Scoring Guide page.');
    if (confirmed) {
        await completeTutorial();
    }
}

async function checkAuth() {
    try {
        const response = await fetch('/api/auth/me');
        const path = window.location.pathname;
        
        if (response.status === 401) {
            if (path === '/login' || path === '/register' || path === '/forgot-password' || path === '/reset-password') {
                hideLandingPage();
                showAuthModal();
                if (path === '/register') {
                    showRegister();
                } else if (path === '/forgot-password') {
                    showForgotPassword();
                } else if (path === '/reset-password') {
                    showResetPassword();
                } else {
                    showLogin();
                }
                const params = new URLSearchParams(window.location.search);
                if (params.get('register') === '1') {
                    showRegister();
                }
            } else {
                showLandingPage();
                updateLandingButtons(false);
            }
            return false;
        }
        
        const data = await response.json();
        
        if (response.ok) {
            currentUser = data;
            apiKeysStatus = data.api_keys_status || {};
            hideLandingPage();
            hideAuthModal();
            updateUserUI();
            loadCredits();
            checkAdminAccess(data);
            showPage('dashboard');
            
            return true;
        } else {
            if (path === '/login' || path === '/register') {
                hideLandingPage();
                showAuthModal();
                if (path === '/register') showRegister();
                else showLogin();
            } else {
                showLandingPage();
                updateLandingButtons(false);
            }
            return false;
        }
    } catch (error) {
        console.error('Error checking auth:', error);
        const path = window.location.pathname;
        if (path === '/login' || path === '/register') {
            hideLandingPage();
            showAuthModal();
            if (path === '/register') showRegister();
            else showLogin();
        } else {
            showLandingPage();
            updateLandingButtons(false);
        }
        return false;
    }
}

function updateLandingButtons(isLoggedIn) {
    const loginBtn = document.getElementById('landingLoginBtn');
    const registerBtn = document.getElementById('landingRegisterBtn');
    const dashboardLink = document.getElementById('landingDashboardLink');
    const creditsLink = document.getElementById('landingCreditsLink');
    const logoutLink = document.getElementById('landingLogoutLink');
    
    if (isLoggedIn) {
        if (loginBtn) loginBtn.style.display = 'none';
        if (registerBtn) registerBtn.style.display = 'none';
        if (dashboardLink) dashboardLink.style.display = 'block';
        if (creditsLink) creditsLink.style.display = 'flex';
        if (logoutLink) logoutLink.style.display = 'inline';
    } else {
        if (loginBtn) loginBtn.style.display = 'block';
        if (registerBtn) registerBtn.style.display = 'block';
        if (dashboardLink) dashboardLink.style.display = 'none';
        if (creditsLink) creditsLink.style.display = 'none';
        if (logoutLink) logoutLink.style.display = 'none';
    }
}

function goToDashboardWithTutorial() {
    hideLandingPage();
    showPage('dashboard');
    if (currentUser && currentUser.user && currentUser.user.completed_tutorial === false) {
        setTimeout(() => {
            showTutorialModal();
        }, 500);
    }
}

function checkAPIKeys(service) {
    if (service === 'twilio') {
        return apiKeysStatus.twilio === true;
    } else if (service === 'hunter') {
        return apiKeysStatus.hunter === true;
    }
    return false;
}

function showMissingKeysModal(service, feature) {
    const serviceNames = {
        'sendgrid': 'SendGrid',
        'twilio': 'Twilio',
        'hunter': 'Hunter.io'
    };
    
    const serviceName = serviceNames[service] || service;
    const message = `To use ${feature}, please configure your ${serviceName} API keys in Settings.`;
    
    document.getElementById('missingKeysMessage').textContent = message;
    document.getElementById('missingKeysModal').style.display = 'flex';
}

function closeMissingKeysModal() {
    document.getElementById('missingKeysModal').style.display = 'none';
}

function goToSettings() {
    closeMissingKeysModal();
    showPage('settings');
}

function showAuthModal() {
    document.getElementById('authModal').style.display = 'flex';
    document.querySelector('.container').style.display = 'none';
    document.querySelector('.top-nav').style.display = 'none';
}

function hideAuthModal() {
    document.getElementById('authModal').style.display = 'none';
    // Only show app navigation if landing page is not visible
    if (!isLandingPageVisible) {
        document.querySelector('.container').style.display = 'block';
        document.querySelector('.top-nav').style.display = 'block';
    }
}

function closeAuthModal() {
    document.getElementById('authModal').style.display = 'none';
    const path = window.location.pathname;
    if (path === '/login' || path === '/register' || path === '/forgot-password' || path === '/reset-password') {
        window.location.href = '/';
    } else {
        showLandingPage();
    }
}

function updateUserUI() {
    const userEmail = currentUser?.user?.email || currentUser?.email;
    if (userEmail) {
        const settingsEmail = document.getElementById('settingsUserEmail');
        if (settingsEmail) {
            settingsEmail.textContent = userEmail;
        }
    }
}

function showLogin() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('forgotPasswordForm').style.display = 'none';
    document.getElementById('resetPasswordForm').style.display = 'none';
    document.getElementById('loginError').textContent = '';
    document.getElementById('registerError').textContent = '';
}

function showRegister() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'block';
    document.getElementById('forgotPasswordForm').style.display = 'none';
    document.getElementById('resetPasswordForm').style.display = 'none';
    document.getElementById('loginError').textContent = '';
    document.getElementById('registerError').textContent = '';
}

function showForgotPassword() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('forgotPasswordForm').style.display = 'block';
    document.getElementById('resetPasswordForm').style.display = 'none';
    document.getElementById('forgotPasswordError').textContent = '';
    document.getElementById('forgotPasswordSuccess').style.display = 'none';
}

function showResetPassword() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('forgotPasswordForm').style.display = 'none';
    document.getElementById('resetPasswordForm').style.display = 'block';
    document.getElementById('resetPasswordError').textContent = '';
    document.getElementById('resetPasswordSuccess').style.display = 'none';
}

let resetToken = null;

async function requestPasswordReset() {
    const email = document.getElementById('forgotEmail').value;
    
    if (!email) {
        document.getElementById('forgotPasswordError').textContent = 'Please enter your email address';
        return;
    }
    
    try {
        const response = await fetch('/api/auth/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('forgotPasswordError').textContent = '';
            document.getElementById('forgotPasswordSuccess').textContent = data.message;
            document.getElementById('forgotPasswordSuccess').style.display = 'block';
        } else {
            document.getElementById('forgotPasswordError').textContent = data.detail || 'An error occurred';
        }
    } catch (error) {
        document.getElementById('forgotPasswordError').textContent = 'An error occurred. Please try again.';
    }
}

async function resetPassword() {
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (!newPassword || !confirmPassword) {
        document.getElementById('resetPasswordError').textContent = 'Please fill in both password fields';
        return;
    }
    
    if (newPassword !== confirmPassword) {
        document.getElementById('resetPasswordError').textContent = 'Passwords do not match';
        return;
    }
    
    if (newPassword.length < 6) {
        document.getElementById('resetPasswordError').textContent = 'Password must be at least 6 characters';
        return;
    }
    
    if (!resetToken) {
        document.getElementById('resetPasswordError').textContent = 'Invalid reset link. Please request a new one.';
        return;
    }
    
    try {
        const response = await fetch('/api/auth/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: resetToken, new_password: newPassword })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('resetPasswordError').textContent = '';
            document.getElementById('resetPasswordSuccess').textContent = data.message;
            document.getElementById('resetPasswordSuccess').style.display = 'block';
            resetToken = null;
            window.history.replaceState({}, document.title, window.location.pathname);
            setTimeout(() => showLogin(), 3000);
        } else {
            document.getElementById('resetPasswordError').textContent = data.detail || 'An error occurred';
        }
    } catch (error) {
        document.getElementById('resetPasswordError').textContent = 'An error occurred. Please try again.';
    }
}

function checkResetToken() {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (token) {
        resetToken = token;
        showResetPassword();
    }
}

async function login() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    if (!email || !password) {
        document.getElementById('loginError').textContent = 'Please enter email and password';
        return;
    }
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            if (typeof gtag === 'function') {
                gtag('event', 'login', { method: 'email' });
            }
            // Set user data and go directly to dashboard
            currentUser = data;
            apiKeysStatus = data.api_keys_status || {};
            hideLandingPage();
            hideAuthModal();
            updateUserUI();
            loadCredits();
            checkAdminAccess(data);
            showPage('dashboard');
            
            // Load initial data
            loadCampaigns();
            loadLeads();
            loadAnalytics();
            loadOAuthStatus();
            loadEmailSignature();
            loadEmailTemplates();
        } else {
            document.getElementById('loginError').textContent = data.detail || 'Login failed';
        }
    } catch (error) {
        document.getElementById('loginError').textContent = `Error: ${error.message}`;
    }
}

async function register() {
    const name = document.getElementById('registerName').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const privacyCheckbox = document.getElementById('privacyAgree');
    
    if (!name || !email || !password) {
        document.getElementById('registerError').textContent = 'Please fill in all fields';
        return;
    }
    
    if (privacyCheckbox && !privacyCheckbox.checked) {
        document.getElementById('registerError').textContent = 'You must agree to the Privacy Policy to register';
        return;
    }
    
    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, full_name: name })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            if (typeof gtag === 'function') {
                gtag('event', 'sign_up', { method: 'email' });
            }
            // Set user data and go directly to dashboard
            currentUser = data;
            apiKeysStatus = data.api_keys_status || {};
            hideLandingPage();
            hideAuthModal();
            updateUserUI();
            loadCredits();
            checkAdminAccess(data);
            
            // Show tutorial for new users
            if (currentUser && currentUser.user && currentUser.user.completed_tutorial === false) {
                showPage('dashboard');
                setTimeout(() => {
                    showTutorialModal();
                }, 500);
            } else {
                showPage('dashboard');
            }
            
            // Load initial data
            loadCampaigns();
            loadLeads();
            loadAnalytics();
            loadOAuthStatus();
            loadEmailSignature();
            loadEmailTemplates();
        } else {
            document.getElementById('registerError').textContent = data.detail || 'Registration failed';
        }
    } catch (error) {
        document.getElementById('registerError').textContent = `Error: ${error.message}`;
    }
}

async function logout() {
    const confirmed = confirm('Are you sure you want to logout?');
    if (!confirmed) return;
    
    try {
        await fetch('/api/auth/logout', { 
            method: 'POST',
            credentials: 'include'
        });
    } catch (error) {
        console.error('Logout error:', error);
    }
    
    // Clear all client-side state
    currentUser = null;
    apiKeysStatus = {};
    userCredits = { balance: 0, total_purchased: 0, total_used: 0 };
    currentLeads = [];
    
    // Clear any localStorage/sessionStorage if used
    localStorage.removeItem('session_token');
    sessionStorage.clear();
    
    // Update UI to logged-out state
    updateLandingButtons(false);
    showLandingPage();
    
    window.location.href = '/';
}

async function loadUserSettings() {
    // Update user email display
    updateUserUI();
    
    try {
        const response = await fetch('/api/user/api-keys');
        
        if (response.ok) {
            const data = await response.json();
            
            document.getElementById('twilioAccountSid').value = data.twilio_account_sid || '';
            document.getElementById('twilioAuthToken').value = data.twilio_auth_token || '';
            document.getElementById('twilioPhoneNumber').value = data.twilio_phone_number || '';
            document.getElementById('hunterApiKey').value = data.hunter_api_key || '';
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
    
    loadEmailProviderStatus();
}

async function saveUserSettings() {
    const settings = {
        twilio_account_sid: document.getElementById('twilioAccountSid').value,
        twilio_auth_token: document.getElementById('twilioAuthToken').value,
        twilio_phone_number: document.getElementById('twilioPhoneNumber').value,
        hunter_api_key: document.getElementById('hunterApiKey').value
    };
    
    try {
        const response = await fetch('/api/user/api-keys', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showStatus('settingsStatus', 'Settings saved successfully!', 'success');
            await checkAuth();
            setTimeout(() => showStatus('settingsStatus', '', ''), 3000);
        } else {
            showStatus('settingsStatus', `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('settingsStatus', `Error: ${error.message}`, 'error');
    }
}

async function loadEmailProviderStatus() {
    try {
        const response = await fetch('/api/email/settings/status');
        if (response.status === 401) {
            return;
        }
        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            console.error('loadEmailProviderStatus: non-JSON response');
            return;
        }
        
        if (response.ok) {
            const data = await response.json();
            
            const statusIcon = document.getElementById('emailStatusIcon');
            const providerName = document.getElementById('emailProviderName');
            const providerEmail = document.getElementById('emailProviderEmail');
            const disconnectBtn = document.getElementById('disconnectEmailBtn');
            
            if (data.configured) {
                statusIcon.textContent = '✅';
                
                const providerDisplayNames = {
                    'gmail': 'Gmail',
                    'outlook': 'Outlook',
                    'smtp': 'SMTP Server',
                    'sendgrid': 'SendGrid'
                };
                
                providerName.textContent = `Connected: ${providerDisplayNames[data.provider] || data.provider}`;
                providerEmail.textContent = data.email || '';
                disconnectBtn.style.display = 'inline-block';
                
                selectEmailProvider(data.provider);
            } else {
                statusIcon.textContent = '⚪';
                providerName.textContent = 'No provider connected';
                providerEmail.textContent = 'Select a provider below to get started';
                disconnectBtn.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error loading email provider status:', error);
    }
}

function selectEmailProvider(provider) {
    const allConfigs = document.querySelectorAll('.provider-config');
    allConfigs.forEach(config => config.style.display = 'none');
    
    const allCards = document.querySelectorAll('.provider-card');
    allCards.forEach(card => {
        card.style.border = '2px solid #e5e7eb';
        card.style.background = '#ffffff';
    });
    
    const selectedCard = event?.currentTarget;
    if (selectedCard) {
        selectedCard.style.border = '2px solid #8b5cf6';
        selectedCard.style.background = 'rgba(139, 92, 246, 0.08)';
    }
    
    const configId = `${provider}Config`;
    const configElement = document.getElementById(configId);
    if (configElement) {
        configElement.style.display = 'block';
    }
}

async function connectGmail() {
    try {
        const response = await fetch('/api/email/auth/gmail/url');
        const data = await response.json();
        
        if (response.ok && data.auth_url) {
            const width = 600;
            const height = 700;
            const left = (screen.width - width) / 2;
            const top = (screen.height - height) / 2;
            
            const authWindow = window.open(
                data.auth_url,
                'Gmail OAuth',
                `width=${width},height=${height},left=${left},top=${top}`
            );
            
            const checkWindowClosed = setInterval(() => {
                if (authWindow.closed) {
                    clearInterval(checkWindowClosed);
                    setTimeout(() => {
                        loadEmailProviderStatus();
                        showStatus('settingsStatus', 'Checking Gmail connection...', 'info');
                    }, 1000);
                }
            }, 500);
        } else {
            showStatus('settingsStatus', `Error: ${data.detail || 'Gmail OAuth not configured. Please add GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_REDIRECT_URI to Secrets.'}`, 'error');
        }
    } catch (error) {
        showStatus('settingsStatus', `Error: ${error.message}`, 'error');
    }
}

async function connectOutlook() {
    try {
        const response = await fetch('/api/email/auth/outlook/url');
        const data = await response.json();
        
        if (response.ok && data.auth_url) {
            const width = 600;
            const height = 700;
            const left = (screen.width - width) / 2;
            const top = (screen.height - height) / 2;
            
            const authWindow = window.open(
                data.auth_url,
                'Outlook OAuth',
                `width=${width},height=${height},left=${left},top=${top}`
            );
            
            const checkWindowClosed = setInterval(() => {
                if (authWindow.closed) {
                    clearInterval(checkWindowClosed);
                    setTimeout(() => {
                        loadEmailProviderStatus();
                        showStatus('settingsStatus', 'Checking Outlook connection...', 'info');
                    }, 1000);
                }
            }, 500);
        } else {
            showStatus('settingsStatus', `Error: ${data.detail || 'Outlook OAuth not configured. Please add MS_CLIENT_ID, MS_CLIENT_SECRET, and MS_REDIRECT_URI to Secrets.'}`, 'error');
        }
    } catch (error) {
        showStatus('settingsStatus', `Error: ${error.message}`, 'error');
    }
}

async function saveSmtpSettings() {
    const smtpSettings = {
        smtp_host: document.getElementById('smtpHost').value,
        smtp_port: parseInt(document.getElementById('smtpPort').value) || 587,
        smtp_username: document.getElementById('smtpUsername').value,
        smtp_password: document.getElementById('smtpPassword').value,
        smtp_from_email: document.getElementById('smtpFromEmail').value,
        smtp_use_tls: document.getElementById('smtpUseTls').checked
    };
    
    if (!smtpSettings.smtp_host || !smtpSettings.smtp_username || !smtpSettings.smtp_password || !smtpSettings.smtp_from_email) {
        showStatus('settingsStatus', 'Please fill in all SMTP fields', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/email/settings/smtp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(smtpSettings)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showStatus('settingsStatus', 'SMTP settings saved successfully!', 'success');
            
            const statusIcon = document.getElementById('emailStatusIcon');
            const providerName = document.getElementById('emailProviderName');
            const providerEmail = document.getElementById('emailProviderEmail');
            const disconnectBtn = document.getElementById('disconnectEmailBtn');
            if (statusIcon) statusIcon.textContent = '✅';
            if (providerName) providerName.textContent = 'Connected: SMTP Server';
            if (providerEmail) providerEmail.textContent = smtpSettings.smtp_from_email;
            if (disconnectBtn) disconnectBtn.style.display = 'inline-block';
            
            loadEmailProviderStatus();
            setTimeout(() => showStatus('settingsStatus', '', ''), 3000);
        } else {
            showStatus('settingsStatus', `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('settingsStatus', `Error: ${error.message}`, 'error');
    }
}

async function saveSendgridSettings() {
    const apiKey = document.getElementById('sendgridApiKeyConfig').value;
    const fromEmail = document.getElementById('sendgridFromEmailConfig').value;
    
    if (!apiKey || !fromEmail) {
        showStatus('settingsStatus', 'Please fill in all SendGrid fields', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/email/settings/sendgrid', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_key: apiKey,
                from_email: fromEmail
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showStatus('settingsStatus', 'SendGrid settings saved successfully!', 'success');
            loadEmailProviderStatus();
            setTimeout(() => showStatus('settingsStatus', '', ''), 3000);
        } else {
            showStatus('settingsStatus', `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('settingsStatus', `Error: ${error.message}`, 'error');
    }
}

async function disconnectEmailProvider() {
    const confirmed = confirm('Are you sure you want to disconnect your email provider? You will need to reconnect to send emails.');
    
    if (!confirmed) return;
    
    try {
        const response = await fetch('/api/email/settings/disconnect', {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showStatus('settingsStatus', 'Email provider disconnected successfully', 'success');
            loadEmailProviderStatus();
            setTimeout(() => showStatus('settingsStatus', '', ''), 3000);
        } else {
            showStatus('settingsStatus', `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('settingsStatus', `Error: ${error.message}`, 'error');
    }
}

function showTestEmailModal() {
    const defaultEmail = currentUser?.email || '';
    const modalHtml = `
        <div id="testEmailModal" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        ">
            <div style="
                background: white;
                padding: 24px;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                max-width: 400px;
                width: 90%;
            ">
                <h3 style="margin: 0 0 16px 0; color: #333;">Send Test Email</h3>
                <p style="color: #666; margin-bottom: 12px;">Enter email address to send test to:</p>
                <input type="email" id="testEmailInput" value="${defaultEmail}" style="
                    width: 100%;
                    padding: 12px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    font-size: 1rem;
                    box-sizing: border-box;
                " placeholder="your@email.com">
                <div style="display: flex; gap: 12px; margin-top: 16px; justify-content: flex-end;">
                    <button onclick="document.getElementById('testEmailModal').remove()" style="
                        padding: 10px 20px;
                        border: 1px solid #ddd;
                        background: white;
                        border-radius: 8px;
                        cursor: pointer;
                    ">Cancel</button>
                    <button onclick="confirmSendTestEmail()" style="
                        padding: 10px 20px;
                        background: linear-gradient(135deg, #4a6cf7 0%, #3b5ce5 100%);
                        color: white;
                        border: none;
                        border-radius: 8px;
                        cursor: pointer;
                        font-weight: 500;
                    ">Send Test</button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    document.getElementById('testEmailInput').focus();
    document.getElementById('testEmailInput').select();
}

async function confirmSendTestEmail() {
    const testEmail = document.getElementById('testEmailInput').value.trim();
    document.getElementById('testEmailModal').remove();
    
    if (!testEmail) return;
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(testEmail)) {
        showStatus('settingsStatus', 'Please enter a valid email address', 'error');
        return;
    }
    
    showStatus('settingsStatus', 'Sending test email...', 'info');
    
    try {
        const response = await fetch('/api/email/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ to_email: testEmail })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showStatus('settingsStatus', `Test email sent successfully to ${testEmail}!`, 'success');
            setTimeout(() => showStatus('settingsStatus', '', ''), 5000);
        } else {
            showStatus('settingsStatus', `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('settingsStatus', `Error: ${error.message}`, 'error');
    }
}

async function sendTestEmail() {
    showTestEmailModal();
}

document.getElementById('loginPassword')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') login();
});

document.getElementById('registerPassword')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') register();
});

checkAuth().then(authenticated => {
    if (authenticated) {
        loadCampaigns();
        loadLeads();
        loadAnalytics();
        loadOAuthStatus();
        loadEmailSignature();
        loadEmailTemplates();
    }
});

async function showScoreBreakdown(leadId) {
    const modal = document.getElementById('scoreBreakdownModal');
    
    // Try to use cached lead data first (instant!)
    const lead = currentLeads.find(l => l.id === leadId);
    
    if (lead && lead.score_reasoning) {
        // Use cached data - instant display
        currentScoreBreakdown = {
            lead_id: lead.id,
            lead_name: lead.name,
            score: lead.score,
            reasoning: lead.score_reasoning
        };
        modal.classList.add('show');
        displayScoreBreakdown(currentScoreBreakdown);
        return;
    }
    
    // If lead exists but no score_reasoning, show helpful message
    if (lead && !lead.score_reasoning) {
        alert('No score breakdown available for this lead. Try scoring it with AI first.');
        return;
    }
    
    // Fallback to API if not in cache
    currentScoreBreakdown = null;
    
    document.getElementById('scoreModalTitle').textContent = 'Score Breakdown';
    document.getElementById('scoreTotal').textContent = 'Loading...';
    document.getElementById('scoreComponents').innerHTML = '<p style="text-align: center; color: #aaa;">Loading breakdown...</p>';
    document.getElementById('scoreSummary').textContent = 'Loading...';
    document.getElementById('scoreRecommendation').textContent = 'Loading...';
    
    modal.classList.add('show');
    
    try {
        const response = await fetch(`/api/leads/${leadId}/score-breakdown`);
        
        if (!response.ok) {
            modal.classList.remove('show');
            if (response.status === 404) {
                alert('No score breakdown available for this lead. Try scoring it with AI first.');
            } else {
                const errorData = await response.json().catch(() => ({}));
                console.error('Score breakdown error:', response.status, errorData);
                alert('Failed to load score breakdown. Please try again.');
            }
            return;
        }
        
        const data = await response.json();
        displayScoreBreakdown(data);
        
    } catch (error) {
        console.error('Error fetching score breakdown:', error);
        modal.classList.remove('show');
        alert('Error loading score breakdown: ' + error.message);
    }
}

function closeScoreBreakdown() {
    const modal = document.getElementById('scoreBreakdownModal');
    modal.classList.remove('show');
}

// Close modal when clicking outside of it
document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('scoreBreakdownModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeScoreBreakdown();
            }
        });
    }
});

function displayScoreBreakdown(data) {
    const modal = document.getElementById('scoreBreakdownModal');
    const { lead_name, score, reasoning } = data;
    
    // Store for email composition
    currentScoreBreakdown = data;
    
    document.getElementById('scoreModalTitle').textContent = `Score Breakdown: ${lead_name}`;
    document.getElementById('scoreTotal').textContent = `${score}/100`;
    
    const componentsContainer = document.getElementById('scoreComponents');
    componentsContainer.innerHTML = '';
    
    // Check for bot-blocking detection (highest priority warning)
    const botBlocked = reasoning.bot_blocked || false;
    const sophisticationMessage = reasoning.sophistication_message || '';
    
    if (botBlocked && sophisticationMessage) {
        const botBlockedDiv = document.createElement('div');
        botBlockedDiv.style.cssText = 'background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 2px solid #a855f7; box-shadow: 0 4px 16px rgba(139, 92, 246, 0.3);';
        botBlockedDiv.innerHTML = `
            <div style="display: flex; align-items: start; gap: 14px;">
                <div style="font-size: 32px; line-height: 1;">🛡️</div>
                <div style="flex: 1; color: white;">
                    <div style="font-weight: 700; font-size: 16px; margin-bottom: 10px;">ADVANCED SECURITY DETECTED</div>
                    <div style="font-size: 14px; line-height: 1.6; opacity: 0.95;">
                        ${sophisticationMessage.replace(/\*\*/g, '<strong>').replace(/🛡️ /g, '')}
                    </div>
                </div>
            </div>
        `;
        componentsContainer.appendChild(botBlockedDiv);
    }
    
    // Detect potential false positive (modern JS-heavy site)
    const renderingLimitations = reasoning.rendering_limitations || false;
    const lowWordCount = reasoning.evidence?.text_word_count < 120;
    const lowScore = score <= 40;
    const showJSWarning = (lowScore || renderingLimitations || lowWordCount) && !botBlocked;
    
    // Add JavaScript rendering warning if needed (skip if bot-blocked already shown)
    if (showJSWarning) {
        const warningDiv = document.createElement('div');
        warningDiv.style.cssText = 'background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); border-radius: 8px; padding: 14px; margin-bottom: 16px; border: 2px solid #f97316; box-shadow: 0 2px 8px rgba(251, 191, 36, 0.3);';
        warningDiv.innerHTML = `
            <div style="display: flex; align-items: start; gap: 10px;">
                <div style="font-size: 24px; line-height: 1;">⚠️</div>
                <div style="flex: 1;">
                    <div style="font-weight: 700; color: #78350f; margin-bottom: 6px; font-size: 14px;">Check the Website Yourself!</div>
                    <div style="color: #92400e; font-size: 13px; line-height: 1.5;">
                        Modern websites using JavaScript frameworks (React, Next.js, etc.) may appear weak to our automated review because their content loads dynamically. 
                        <strong style="color: #78350f;">Always view the website before dismissing this lead</strong> - it might be more sophisticated than the score suggests.
                    </div>
                </div>
            </div>
        `;
        componentsContainer.appendChild(warningDiv);
    }
    
    // Add Rendering Pathway Badge
    const renderPathway = reasoning.render_pathway;
    const jsDetected = reasoning.js_detected || false;
    const jsConfidence = reasoning.js_confidence || 0;
    const frameworkHints = reasoning.framework_hints || [];
    
    if (renderPathway || jsDetected) {
        const pathwayDiv = document.createElement('div');
        pathwayDiv.style.cssText = 'margin-bottom: 16px;';
        
        let badgeColor, badgeIcon, badgeText, badgeDetails;
        
        if (renderPathway === 'rendered') {
            badgeColor = '#10b981'; // Green
            badgeIcon = '🎭';
            badgeText = 'Fully Rendered';
            badgeDetails = 'JavaScript executed - showing actual content';
        } else if (renderPathway === 'render_failed') {
            badgeColor = '#ef4444'; // Red
            badgeIcon = '⚠️';
            badgeText = 'Rendering Failed';
            badgeDetails = 'Attempted JS rendering but failed - using static HTML';
        } else if (jsDetected) {
            badgeColor = '#f59e0b'; // Orange
            badgeIcon = '⚡';
            badgeText = 'JS Framework Detected';
            badgeDetails = `${frameworkHints.join(', ') || 'Modern framework'} - may need rendering`;
        } else {
            badgeColor = '#6b7280'; // Gray
            badgeIcon = '📄';
            badgeText = 'Static HTML';
            badgeDetails = 'Standard website - no JavaScript rendering needed';
        }
        
        pathwayDiv.innerHTML = `
            <div style="display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px; background: rgba(255, 255, 255, 0.05); border-radius: 6px; border: 1px solid ${badgeColor}40;">
                <span style="font-size: 16px;">${badgeIcon}</span>
                <div>
                    <div style="font-weight: 600; color: ${badgeColor}; font-size: 13px;">${badgeText}</div>
                    <div style="font-size: 11px; color: #999; margin-top: 2px;">${badgeDetails}</div>
                    ${frameworkHints.length > 0 ? `<div style="font-size: 10px; color: #666; margin-top: 2px;">Frameworks: ${frameworkHints.join(', ')}</div>` : ''}
                </div>
            </div>
        `;
        
        componentsContainer.appendChild(pathwayDiv);
    }
    
    // Check if this is new hybrid scoring
    const isHybrid = reasoning.hybrid_breakdown && reasoning.hybrid_breakdown.heuristic_score !== undefined;
    
    if (isHybrid) {
        // Display hybrid scoring breakdown
        const hybrid = reasoning.hybrid_breakdown;
        const confidence = reasoning.confidence || 0.5;
        
        // Overall breakdown section
        const overallDiv = document.createElement('div');
        overallDiv.style.cssText = 'background: rgba(88, 28, 135, 0.15); border-radius: 8px; padding: 12px; margin-bottom: 16px; border: 1px solid rgba(168, 85, 247, 0.3);';
        overallDiv.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 600; color: #111827;">Hybrid Score Breakdown</span>
                <span style="font-size: 12px; color: #6b7280;">${confidence >= 0.7 ? 'High' : confidence >= 0.4 ? 'Medium' : 'Low'} Confidence</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                <div style="background: rgba(34, 197, 94, 0.15); border-radius: 6px; padding: 10px; border: 1px solid rgba(34, 197, 94, 0.3);">
                    <div style="font-size: 13px; color: #374151; margin-bottom: 4px;">Technical Checks</div>
                    <div style="font-size: 24px; font-weight: 700; color: #16a34a;">${hybrid.heuristic_score}/50</div>
                    <div style="font-size: 11px; color: #6b7280; margin-top: 2px;">Automated analysis</div>
                </div>
                <div style="background: rgba(147, 51, 234, 0.15); border-radius: 6px; padding: 10px; border: 1px solid rgba(147, 51, 234, 0.3);">
                    <div style="font-size: 13px; color: #374151; margin-bottom: 4px;">AI Review</div>
                    <div style="font-size: 24px; font-weight: 700; color: #7c3aed;">${hybrid.ai_score}/50</div>
                    <div style="font-size: 11px; color: #6b7280; margin-top: 2px;">UX, brand, trust</div>
                </div>
            </div>
        `;
        componentsContainer.appendChild(overallDiv);
        
        // Plain English Report section - Most prominent
        if (reasoning.plain_english_report && Object.keys(reasoning.plain_english_report).length > 0) {
            const reportDiv = document.createElement('div');
            reportDiv.style.cssText = 'background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(147, 51, 234, 0.1)); border-radius: 8px; padding: 16px; margin-bottom: 16px; border: 1px solid rgba(99, 102, 241, 0.3);';
            
            const report = reasoning.plain_english_report;
            let reportHTML = '<div style="font-weight: 700; color: #111827; margin-bottom: 12px; font-size: 15px;">📋 Website Analysis Report</div>';
            
            // Strengths
            if (report.strengths && report.strengths.length > 0) {
                reportHTML += '<div style="margin-bottom: 12px;"><div style="font-weight: 600; color: #16a34a; margin-bottom: 6px; font-size: 13px;">✅ Strengths</div>';
                reportHTML += '<ul style="margin: 0; padding-left: 20px; color: #1f2937; font-size: 13px; line-height: 1.6;">';
                report.strengths.forEach(strength => {
                    reportHTML += `<li style="margin-bottom: 4px;">${strength}</li>`;
                });
                reportHTML += '</ul></div>';
            }
            
            // Weaknesses - formatted with implications
            if (report.weaknesses && report.weaknesses.length > 0) {
                reportHTML += '<div style="margin-bottom: 12px;">';
                report.weaknesses.forEach(weakness => {
                    // Generate implication based on weakness type
                    let implication = '';
                    const lowerWeakness = weakness.toLowerCase();
                    if (lowerWeakness.includes('mobile') || lowerWeakness.includes('responsive')) {
                        implication = 'High bounce risk on phones';
                    } else if (lowerWeakness.includes('ssl') || lowerWeakness.includes('https') || lowerWeakness.includes('security')) {
                        implication = 'Trust & search visibility issues';
                    } else if (lowerWeakness.includes('slow') || lowerWeakness.includes('speed') || lowerWeakness.includes('load')) {
                        implication = 'Conversion drop likely';
                    } else if (lowerWeakness.includes('seo') || lowerWeakness.includes('meta')) {
                        implication = 'Lower search rankings';
                    } else if (lowerWeakness.includes('contact') || lowerWeakness.includes('form')) {
                        implication = 'Lost lead opportunities';
                    } else if (lowerWeakness.includes('outdated') || lowerWeakness.includes('old') || lowerWeakness.includes('design')) {
                        implication = 'Poor first impressions';
                    } else if (lowerWeakness.includes('analytics') || lowerWeakness.includes('tracking')) {
                        implication = 'No visitor insights';
                    } else {
                        implication = 'Room for improvement';
                    }
                    reportHTML += `
                        <div style="background: rgba(234, 179, 8, 0.15); border: 1px solid rgba(234, 179, 8, 0.4); border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                            <div style="display: flex; align-items: flex-start; gap: 8px;">
                                <span style="font-size: 16px;">⚠️</span>
                                <div>
                                    <div style="font-weight: 600; color: #92400e; font-size: 13px;">${weakness}</div>
                                    <div style="color: #78350f; font-size: 12px; margin-top: 4px;">→ ${implication}</div>
                                </div>
                            </div>
                        </div>`;
                });
                reportHTML += '</div>';
            }
            
            // Technology Observations
            if (report.technology_observations) {
                reportHTML += '<div style="margin-bottom: 12px;"><div style="font-weight: 600; color: #2563eb; margin-bottom: 6px; font-size: 13px;">🔧 Technology & Tools</div>';
                reportHTML += `<p style="margin: 0; color: #1f2937; font-size: 13px; line-height: 1.6;">${report.technology_observations}</p></div>`;
            }
            
            // Sales Opportunities - Most important for user
            if (report.sales_opportunities && report.sales_opportunities.length > 0) {
                reportHTML += '<div style="margin-bottom: 0;"><div style="font-weight: 600; color: #9333ea; margin-bottom: 6px; font-size: 13px;">💰 Sales Opportunities</div>';
                reportHTML += '<ul style="margin: 0; padding-left: 20px; color: #111827; font-size: 13px; line-height: 1.6; font-weight: 500;">';
                report.sales_opportunities.forEach(opportunity => {
                    reportHTML += `<li style="margin-bottom: 4px;">${opportunity}</li>`;
                });
                reportHTML += '</ul></div>';
            }
            
            reportDiv.innerHTML = reportHTML;
            componentsContainer.appendChild(reportDiv);
        }
        
        // Technology Stack section
        const lead = currentLeads.find(l => l.id === data.lead_id);
        if (lead && lead.technographics && lead.technographics.detected) {
            const techHTML = renderTechSectionFull(lead.technographics);
            if (techHTML) {
                const techDiv = document.createElement('div');
                techDiv.innerHTML = techHTML;
                componentsContainer.appendChild(techDiv.firstElementChild);
            }
        }
        
        // Evidence section
        if (reasoning.evidence && Object.keys(reasoning.evidence).length > 0) {
            const evidenceDiv = document.createElement('div');
            evidenceDiv.style.cssText = 'background: rgba(255, 255, 255, 0.03); border-radius: 8px; padding: 12px; margin-bottom: 16px; border: 1px solid rgba(255, 255, 255, 0.08);';
            evidenceDiv.innerHTML = '<div style="font-weight: 600; color: #111827; margin-bottom: 8px;">📊 Evidence Found</div>';
            
            const evidenceList = document.createElement('div');
            evidenceList.style.cssText = 'display: grid; gap: 6px; font-size: 13px;';
            
            const evidence = reasoning.evidence;
            const items = [];
            
            if (evidence.is_mobile_friendly !== undefined) items.push(`${evidence.is_mobile_friendly ? '✅' : '❌'} Mobile-friendly design`);
            if (evidence.has_ssl !== undefined) items.push(`${evidence.has_ssl ? '✅' : '❌'} SSL/HTTPS security`);
            if (evidence.has_contact_info !== undefined) items.push(`${evidence.has_contact_info ? '✅' : '❌'} Contact information`);
            if (evidence.meta_description !== undefined) items.push(`${evidence.meta_description ? '✅' : '❌'} SEO meta description`);
            if (evidence.has_analytics !== undefined) items.push(`${evidence.has_analytics ? '✅' : '❌'} Analytics tracking`);
            
            items.forEach(item => {
                const itemDiv = document.createElement('div');
                itemDiv.style.color = '#374151';
                itemDiv.textContent = item;
                evidenceList.appendChild(itemDiv);
            });
            
            evidenceDiv.appendChild(evidenceList);
            componentsContainer.appendChild(evidenceDiv);
        }
        
        // AI justifications
        if (reasoning.ai_justifications && Object.keys(reasoning.ai_justifications).length > 0) {
            const justDiv = document.createElement('div');
            justDiv.style.cssText = 'background: rgba(255, 255, 255, 0.03); border-radius: 8px; padding: 12px; border: 1px solid rgba(255, 255, 255, 0.08);';
            justDiv.innerHTML = '<div style="font-weight: 600; color: #111827; margin-bottom: 8px;">💡 AI Insights</div>';
            
            const justList = document.createElement('div');
            justList.style.cssText = 'display: grid; gap: 8px; font-size: 13px;';
            
            Object.entries(reasoning.ai_justifications).forEach(([key, value]) => {
                if (value && value.trim()) {
                    const justItem = document.createElement('div');
                    justItem.style.cssText = 'padding: 8px; background: rgba(255, 255, 255, 0.02); border-radius: 4px; color: #374151;';
                    justItem.innerHTML = `<strong style="color: #7c3aed;">${key}:</strong> ${value}`;
                    justList.appendChild(justItem);
                }
            });
            
            justDiv.appendChild(justList);
            componentsContainer.appendChild(justDiv);
        }
    } else {
        // Legacy scoring display
        const components = [
            { name: 'Website Quality', data: reasoning.website_quality, max: 30 },
            { name: 'Digital Presence', data: reasoning.digital_presence, max: 30 },
            { name: 'Automation & Technology', data: reasoning.automation_opportunity, max: 40 }
        ];
        
        components.forEach(component => {
            const div = document.createElement('div');
            div.className = 'score-component';
            
            const leftDiv = document.createElement('div');
            const nameDiv = document.createElement('div');
            nameDiv.className = 'score-component-name';
            nameDiv.textContent = component.name;
            
            const rationaleDiv = document.createElement('div');
            rationaleDiv.className = 'score-component-rationale';
            rationaleDiv.textContent = component.data?.rationale || 'N/A';
            
            leftDiv.appendChild(nameDiv);
            leftDiv.appendChild(rationaleDiv);
            
            const valueDiv = document.createElement('div');
            valueDiv.className = 'score-component-value';
            valueDiv.textContent = `${component.data?.score || 0}/${component.max}`;
            
            div.appendChild(leftDiv);
            div.appendChild(valueDiv);
            componentsContainer.appendChild(div);
        });
    }
    
    document.getElementById('scoreSummary').textContent = reasoning.summary || 'No summary available';
    document.getElementById('scoreRecommendation').textContent = reasoning.top_recommendation || 'No recommendation available';
    
    // Show/hide compose email button based on email availability
    const composeBtn = document.getElementById('composeFromScoreBtn');
    const lead = currentLeads.find(l => l.id === data.lead_id);
    if (lead && lead.email && lead.email.trim() !== '') {
        composeBtn.style.display = 'block';
    } else {
        composeBtn.style.display = 'none';
    }
    
    modal.style.display = 'block';
}

function closeScoreBreakdown() {
    const modal = document.getElementById('scoreBreakdownModal');
    modal.style.display = 'none';
    // Clear stale data
    currentScoreBreakdown = null;
}

window.onclick = function(event) {
    const modal = document.getElementById('scoreBreakdownModal');
    if (event.target === modal) {
        closeScoreBreakdown();
    }
    const internalModal = document.getElementById('internalReportModal');
    if (event.target === internalModal) {
        closeInternalReport();
    }
    const clientFormModal = document.getElementById('clientReportFormModal');
    if (event.target === clientFormModal) {
        closeClientReportForm();
    }
    const clientPdfModal = document.getElementById('clientPdfFormModal');
    if (event.target === clientPdfModal) {
        closeClientPdfForm();
    }
    const emailPdfModal = document.getElementById('emailPdfFormModal');
    if (event.target === emailPdfModal) {
        closeEmailPdfForm();
    }
};

async function showInternalReport() {
    if (!currentScoreBreakdown || !currentScoreBreakdown.lead_id) {
        alert('No lead selected. Please open a score breakdown first.');
        return;
    }
    const leadId = currentScoreBreakdown.lead_id;
    const btn = document.getElementById('internalReportBtn');
    const origText = btn.innerHTML;
    btn.innerHTML = '⏳ Generating...';
    btn.disabled = true;

    try {
        const response = await fetch(`/api/leads/${leadId}/internal-report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.error || 'Failed to generate internal report');
        }

        const data = await response.json();
        displayInternalReport(data);
    } catch (error) {
        console.error('Internal report error:', error);
        alert('Error generating internal report: ' + error.message);
    } finally {
        btn.innerHTML = origText;
        btn.disabled = false;
    }
}

function displayInternalReport(data) {
    let existing = document.getElementById('internalReportModal');
    if (existing) existing.remove();

    const report = data.report || data;

    const sections = [];

    if (report.business_info || report.lead_name) {
        const info = report.business_info || {};
        sections.push(`
            <div style="margin-bottom: 20px;">
                <div style="background: #1e1b4b; color: white; padding: 10px 16px; border-radius: 8px 8px 0 0; font-weight: 700; font-size: 0.95rem; letter-spacing: 0.5px;">🏢 BUSINESS INFO</div>
                <div style="background: #f5f3ff; padding: 16px; border-radius: 0 0 8px 8px; border: 1px solid #e5e7eb; border-top: none;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.9rem;">
                        ${report.lead_name ? `<div><strong>Name:</strong> ${report.lead_name}</div>` : ''}
                        ${info.website ? `<div><strong>Website:</strong> <a href="${info.website}" target="_blank" style="color: #7c3aed;">${info.website}</a></div>` : ''}
                        ${info.phone ? `<div><strong>Phone:</strong> ${info.phone}</div>` : ''}
                        ${info.email ? `<div><strong>Email:</strong> ${info.email}</div>` : ''}
                        ${info.address ? `<div style="grid-column: 1/-1;"><strong>Address:</strong> ${info.address}</div>` : ''}
                        ${info.industry ? `<div><strong>Industry:</strong> ${info.industry}</div>` : ''}
                    </div>
                </div>
            </div>
        `);
    }

    if (report.score_breakdown || report.score !== undefined) {
        const sb = report.score_breakdown || {};
        sections.push(`
            <div style="margin-bottom: 20px;">
                <div style="background: #1e1b4b; color: white; padding: 10px 16px; border-radius: 8px 8px 0 0; font-weight: 700; font-size: 0.95rem; letter-spacing: 0.5px;">📊 SCORE BREAKDOWN</div>
                <div style="background: #f5f3ff; padding: 16px; border-radius: 0 0 8px 8px; border: 1px solid #e5e7eb; border-top: none;">
                    <div style="text-align: center; margin-bottom: 12px;">
                        <span style="font-size: 2rem; font-weight: 800; color: #7c3aed;">${report.score || sb.total || '--'}</span>
                        <span style="font-size: 1rem; color: #6b7280;">/100</span>
                    </div>
                    ${sb.summary ? `<p style="color: #4b5563; font-size: 0.9rem;">${sb.summary}</p>` : ''}
                    ${sb.components ? `<div style="margin-top: 10px;">${sb.components.map(c => `
                        <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #e5e7eb; font-size: 0.85rem;">
                            <span style="color: #374151;">${c.name || c.category || ''}</span>
                            <span style="font-weight: 600; color: #7c3aed;">${c.score !== undefined ? c.score : c.value || ''}/${c.max || ''}</span>
                        </div>
                    `).join('')}</div>` : ''}
                </div>
            </div>
        `);
    }

    if (report.technographics) {
        const tech = report.technographics;
        const techItems = [];
        if (tech.cms) techItems.push(`<span style="display: inline-block; background: #ede9fe; color: #5b21b6; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; margin: 3px;">CMS: ${tech.cms}</span>`);
        if (tech.frameworks && tech.frameworks.length) tech.frameworks.forEach(f => techItems.push(`<span style="display: inline-block; background: #e0e7ff; color: #3730a3; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; margin: 3px;">${f}</span>`));
        if (tech.analytics && tech.analytics.length) tech.analytics.forEach(a => techItems.push(`<span style="display: inline-block; background: #d1fae5; color: #065f46; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; margin: 3px;">📈 ${a}</span>`));
        if (tech.hosting) techItems.push(`<span style="display: inline-block; background: #fef3c7; color: #92400e; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; margin: 3px;">Hosting: ${tech.hosting}</span>`);
        if (tech.ssl !== undefined) techItems.push(`<span style="display: inline-block; background: ${tech.ssl ? '#d1fae5' : '#fee2e2'}; color: ${tech.ssl ? '#065f46' : '#991b1b'}; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; margin: 3px;">${tech.ssl ? '🔒 SSL' : '⚠️ No SSL'}</span>`);

        if (typeof tech === 'object' && !techItems.length) {
            Object.entries(tech).forEach(([key, val]) => {
                if (val && typeof val === 'string') techItems.push(`<span style="display: inline-block; background: #ede9fe; color: #5b21b6; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; margin: 3px;">${key}: ${val}</span>`);
                if (Array.isArray(val)) val.forEach(v => techItems.push(`<span style="display: inline-block; background: #e0e7ff; color: #3730a3; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; margin: 3px;">${v}</span>`));
            });
        }

        sections.push(`
            <div style="margin-bottom: 20px;">
                <div style="background: #1e1b4b; color: white; padding: 10px 16px; border-radius: 8px 8px 0 0; font-weight: 700; font-size: 0.95rem; letter-spacing: 0.5px;">🔧 TECHNOGRAPHICS</div>
                <div style="background: #f5f3ff; padding: 16px; border-radius: 0 0 8px 8px; border: 1px solid #e5e7eb; border-top: none;">
                    <div style="display: flex; flex-wrap: wrap; gap: 4px;">${techItems.join('') || '<span style="color: #9ca3af;">No technographic data available</span>'}</div>
                </div>
            </div>
        `);
    }

    if (report.ai_analysis) {
        const analysis = typeof report.ai_analysis === 'string' ? report.ai_analysis : JSON.stringify(report.ai_analysis, null, 2);
        sections.push(`
            <div style="margin-bottom: 20px;">
                <div style="background: #1e1b4b; color: white; padding: 10px 16px; border-radius: 8px 8px 0 0; font-weight: 700; font-size: 0.95rem; letter-spacing: 0.5px;">🤖 AI ANALYSIS</div>
                <div style="background: #f5f3ff; padding: 16px; border-radius: 0 0 8px 8px; border: 1px solid #e5e7eb; border-top: none;">
                    <div style="color: #374151; font-size: 0.9rem; line-height: 1.7; white-space: pre-wrap;">${analysis}</div>
                </div>
            </div>
        `);
    }

    if (report.sales_opportunities) {
        const opps = Array.isArray(report.sales_opportunities) ? report.sales_opportunities : [report.sales_opportunities];
        sections.push(`
            <div style="margin-bottom: 20px;">
                <div style="background: #1e1b4b; color: white; padding: 10px 16px; border-radius: 8px 8px 0 0; font-weight: 700; font-size: 0.95rem; letter-spacing: 0.5px;">💰 SALES OPPORTUNITIES</div>
                <div style="background: #f5f3ff; padding: 16px; border-radius: 0 0 8px 8px; border: 1px solid #e5e7eb; border-top: none;">
                    ${opps.map((opp, i) => {
                        if (typeof opp === 'string') return `<div style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; font-size: 0.9rem; color: #374151;">• ${opp}</div>`;
                        return `<div style="padding: 10px 0; ${i < opps.length - 1 ? 'border-bottom: 1px solid #e5e7eb;' : ''}">
                            <div style="font-weight: 600; color: #5b21b6; font-size: 0.9rem;">${opp.title || opp.opportunity || opp.name || ''}</div>
                            ${opp.description ? `<div style="color: #6b7280; font-size: 0.85rem; margin-top: 4px;">${opp.description}</div>` : ''}
                            ${opp.value ? `<div style="color: #059669; font-weight: 600; font-size: 0.85rem; margin-top: 4px;">Est. Value: ${opp.value}</div>` : ''}
                        </div>`;
                    }).join('')}
                </div>
            </div>
        `);
    }

    if (!sections.length) {
        const fallbackContent = typeof report === 'string' ? report : JSON.stringify(report, null, 2);
        sections.push(`
            <div style="margin-bottom: 20px;">
                <div style="background: #1e1b4b; color: white; padding: 10px 16px; border-radius: 8px 8px 0 0; font-weight: 700;">📄 REPORT DATA</div>
                <div style="background: #f5f3ff; padding: 16px; border-radius: 0 0 8px 8px; border: 1px solid #e5e7eb; border-top: none;">
                    <pre style="white-space: pre-wrap; font-size: 0.85rem; color: #374151;">${fallbackContent}</pre>
                </div>
            </div>
        `);
    }

    const modalHtml = `
        <div id="internalReportModal" class="modal" style="display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 10001; align-items: center; justify-content: center; overflow-y: auto;">
            <div style="background: white; border-radius: 16px; max-width: 700px; width: 95%; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.3); margin: 20px;">
                <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); padding: 20px 24px; border-radius: 16px 16px 0 0; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="color: #c4b5fd; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">Internal Intelligence Dossier</div>
                        <div style="color: white; font-size: 1.2rem; font-weight: 700; margin-top: 4px;">${report.lead_name || 'Lead Report'}</div>
                    </div>
                    <span onclick="closeInternalReport()" style="color: white; font-size: 24px; cursor: pointer; opacity: 0.7; transition: opacity 0.2s;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.7">&times;</span>
                </div>
                <div style="padding: 24px;">
                    ${sections.join('')}
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

function closeInternalReport() {
    const modal = document.getElementById('internalReportModal');
    if (modal) modal.remove();
}

function showClientReportForm() {
    if (!currentScoreBreakdown || !currentScoreBreakdown.lead_id) {
        alert('No lead selected. Please open a score breakdown first.');
        return;
    }

    let existing = document.getElementById('clientReportFormModal');
    if (existing) existing.remove();

    const modalHtml = `
        <div id="clientReportFormModal" class="modal" style="display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 10001; align-items: center; justify-content: center;">
            <div style="background: white; border-radius: 16px; max-width: 460px; width: 95%; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
                <div style="background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%); padding: 20px 24px; border-radius: 16px 16px 0 0; display: flex; justify-content: space-between; align-items: center;">
                    <div style="color: white; font-size: 1.1rem; font-weight: 700;">📄 Generate Client Audit Report</div>
                    <span onclick="closeClientReportForm()" style="color: white; font-size: 24px; cursor: pointer; opacity: 0.7;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.7">&times;</span>
                </div>
                <div style="padding: 24px;">
                    <p style="color: #6b7280; font-size: 0.9rem; margin-bottom: 16px;">Customize the report with your agency branding (all fields optional).</p>
                    <div style="margin-bottom: 14px;">
                        <label style="display: block; font-weight: 600; color: #374151; margin-bottom: 4px; font-size: 0.9rem;">Agency Name</label>
                        <input type="text" id="clientReportAgencyName" placeholder="e.g. Acme Digital Agency" style="width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; box-sizing: border-box;">
                    </div>
                    <div style="margin-bottom: 14px;">
                        <label style="display: block; font-weight: 600; color: #374151; margin-bottom: 4px; font-size: 0.9rem;">Agency Website</label>
                        <input type="text" id="clientReportAgencyWebsite" placeholder="e.g. https://acmedigital.com" style="width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; box-sizing: border-box;">
                    </div>
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; font-weight: 600; color: #374151; margin-bottom: 4px; font-size: 0.9rem;">Agency Tagline</label>
                        <input type="text" id="clientReportAgencyTagline" placeholder="e.g. We build websites that convert" style="width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; box-sizing: border-box;">
                    </div>
                    <button id="generateClientReportBtn" onclick="generateClientReport()" style="width: 100%; padding: 14px; font-size: 1rem; background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%); border: none; color: white; border-radius: 10px; cursor: pointer; font-weight: 700; transition: all 0.3s ease;">
                        Generate & Open Report
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

function closeClientReportForm() {
    const modal = document.getElementById('clientReportFormModal');
    if (modal) modal.remove();
}

async function generateClientReport() {
    if (!currentScoreBreakdown || !currentScoreBreakdown.lead_id) {
        alert('No lead selected.');
        return;
    }

    const leadId = currentScoreBreakdown.lead_id;
    const agencyName = document.getElementById('clientReportAgencyName').value.trim();
    const agencyWebsite = document.getElementById('clientReportAgencyWebsite').value.trim();
    const agencyTagline = document.getElementById('clientReportAgencyTagline').value.trim();

    const btn = document.getElementById('generateClientReportBtn');
    const origText = btn.innerHTML;
    btn.innerHTML = '<span style="display: inline-flex; align-items: center; gap: 8px;"><svg width="18" height="18" viewBox="0 0 24 24" style="animation: spin 1s linear infinite;"><style>@keyframes spin{to{transform:rotate(360deg)}}</style><circle cx="12" cy="12" r="10" stroke="white" stroke-width="3" fill="none" stroke-dasharray="31.4" stroke-dashoffset="10"/></svg> Generating Report...</span>';
    btn.disabled = true;

    try {
        const response = await fetch(`/api/leads/${leadId}/client-report-html`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agency_name: agencyName || undefined,
                agency_website: agencyWebsite || undefined,
                agency_tagline: agencyTagline || undefined
            })
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.error || 'Failed to generate client report');
        }

        const data = await response.json();
        const htmlContent = data.html || data.report_html || data.content || '';

        if (!htmlContent) {
            throw new Error('No report HTML returned from server');
        }

        const reportWindow = window.open('', '_blank');
        if (reportWindow) {
            reportWindow.document.write(htmlContent);
            reportWindow.document.close();
        } else {
            alert('Pop-up was blocked. Please allow pop-ups for this site and try again.');
        }

        closeClientReportForm();

    } catch (error) {
        console.error('Client report error:', error);
        alert('Error generating client report: ' + error.message);
    } finally {
        btn.innerHTML = origText;
        btn.disabled = false;
    }
}

async function downloadPdfReport(type, agencyName, agencyWebsite, agencyTagline) {
    if (!currentScoreBreakdown || !currentScoreBreakdown.lead_id) {
        alert('No lead selected. Please open a score breakdown first.');
        return;
    }
    const leadId = currentScoreBreakdown.lead_id;
    const btnId = type === 'internal' ? 'internalPdfBtn' : 'clientPdfBtn';
    const btn = document.getElementById(btnId);
    const origText = btn ? btn.innerHTML : '';
    if (btn) {
        btn.innerHTML = '⏳ Generating...';
        btn.disabled = true;
    }

    try {
        const payload = { type };
        if (type === 'client') {
            if (agencyName) payload.agency_name = agencyName;
            if (agencyWebsite) payload.agency_website = agencyWebsite;
            if (agencyTagline) payload.agency_tagline = agencyTagline;
        }

        const response = await fetch(`/api/leads/${leadId}/report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || err.error || 'Failed to generate PDF report');
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const disposition = response.headers.get('Content-Disposition');
        let filename = `report_${type}.pdf`;
        if (disposition) {
            const match = disposition.match(/filename="?([^"]+)"?/);
            if (match) filename = match[1];
        }
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (error) {
        console.error('PDF report error:', error);
        alert('Error generating PDF: ' + error.message);
    } finally {
        if (btn) {
            btn.innerHTML = origText;
            btn.disabled = false;
        }
    }
}

function showClientPdfForm() {
    if (!currentScoreBreakdown || !currentScoreBreakdown.lead_id) {
        alert('No lead selected. Please open a score breakdown first.');
        return;
    }

    let existing = document.getElementById('clientPdfFormModal');
    if (existing) existing.remove();

    const modalHtml = `
        <div id="clientPdfFormModal" class="modal" style="display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 10001; align-items: center; justify-content: center;">
            <div style="background: white; border-radius: 16px; max-width: 460px; width: 95%; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
                <div style="background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%); padding: 20px 24px; border-radius: 16px 16px 0 0; display: flex; justify-content: space-between; align-items: center;">
                    <div style="color: white; font-size: 1.1rem; font-weight: 700;">📥 Download Client PDF Report</div>
                    <span onclick="closeClientPdfForm()" style="color: white; font-size: 24px; cursor: pointer; opacity: 0.7;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.7">&times;</span>
                </div>
                <div style="padding: 24px;">
                    <p style="color: #6b7280; font-size: 0.9rem; margin-bottom: 16px;">Customize the PDF with your agency branding (all fields optional).</p>
                    <div style="margin-bottom: 14px;">
                        <label style="display: block; font-weight: 600; color: #374151; margin-bottom: 4px; font-size: 0.9rem;">Agency Name</label>
                        <input type="text" id="clientPdfAgencyName" placeholder="e.g. Acme Digital Agency" style="width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; box-sizing: border-box;">
                    </div>
                    <div style="margin-bottom: 14px;">
                        <label style="display: block; font-weight: 600; color: #374151; margin-bottom: 4px; font-size: 0.9rem;">Agency Website</label>
                        <input type="text" id="clientPdfAgencyWebsite" placeholder="e.g. https://acmedigital.com" style="width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; box-sizing: border-box;">
                    </div>
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; font-weight: 600; color: #374151; margin-bottom: 4px; font-size: 0.9rem;">Agency Tagline</label>
                        <input type="text" id="clientPdfAgencyTagline" placeholder="e.g. We build websites that convert" style="width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; box-sizing: border-box;">
                    </div>
                    <button id="downloadClientPdfBtn" onclick="submitClientPdfForm()" style="width: 100%; padding: 14px; font-size: 1rem; background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%); border: none; color: white; border-radius: 10px; cursor: pointer; font-weight: 700; transition: all 0.3s ease;">
                        Download PDF
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

function closeClientPdfForm() {
    const modal = document.getElementById('clientPdfFormModal');
    if (modal) modal.remove();
}

async function submitClientPdfForm() {
    const agencyName = document.getElementById('clientPdfAgencyName').value.trim();
    const agencyWebsite = document.getElementById('clientPdfAgencyWebsite').value.trim();
    const agencyTagline = document.getElementById('clientPdfAgencyTagline').value.trim();
    closeClientPdfForm();
    await downloadPdfReport('client', agencyName, agencyWebsite, agencyTagline);
}

function showEmailPdfForm() {
    if (!currentScoreBreakdown || !currentScoreBreakdown.lead_id) {
        alert('No lead selected. Please open a score breakdown first.');
        return;
    }

    const lead = currentLeads.find(l => l.id === currentScoreBreakdown.lead_id);
    const leadEmail = lead ? lead.email : '';
    const leadName = lead ? (lead.contact_name || lead.name) : '';

    if (!leadEmail) {
        alert('This lead has no email address. Please add an email first.');
        return;
    }

    let existing = document.getElementById('emailPdfFormModal');
    if (existing) existing.remove();

    const modalHtml = `
        <div id="emailPdfFormModal" class="modal" style="display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 10001; align-items: center; justify-content: center;">
            <div style="background: white; border-radius: 16px; max-width: 520px; width: 95%; box-shadow: 0 20px 60px rgba(0,0,0,0.3); max-height: 90vh; overflow-y: auto;">
                <div style="background: linear-gradient(135deg, #059669 0%, #10b981 100%); padding: 20px 24px; border-radius: 16px 16px 0 0; display: flex; justify-content: space-between; align-items: center;">
                    <div style="color: white; font-size: 1.1rem; font-weight: 700;">📧 Email PDF Report</div>
                    <span onclick="closeEmailPdfForm()" style="color: white; font-size: 24px; cursor: pointer; opacity: 0.7;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.7">&times;</span>
                </div>
                <div style="padding: 24px;">
                    <p style="color: #6b7280; font-size: 0.9rem; margin-bottom: 16px;">Generate a PDF report and send it directly to <b>${leadEmail}</b>.</p>
                    <div style="margin-bottom: 14px;">
                        <label style="display: block; font-weight: 600; color: #374151; margin-bottom: 4px; font-size: 0.9rem;">Report Type</label>
                        <select id="emailPdfType" style="width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; box-sizing: border-box;">
                            <option value="client">Client Audit Report</option>
                            <option value="internal">Internal Report</option>
                        </select>
                    </div>
                    <div style="margin-bottom: 14px;">
                        <label style="display: block; font-weight: 600; color: #374151; margin-bottom: 4px; font-size: 0.9rem;">Email Subject (optional)</label>
                        <input type="text" id="emailPdfSubject" placeholder="Auto-generated if left blank" style="width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; box-sizing: border-box;">
                    </div>
                    <div style="margin-bottom: 14px;">
                        <label style="display: block; font-weight: 600; color: #374151; margin-bottom: 4px; font-size: 0.9rem;">Email Body (optional)</label>
                        <textarea id="emailPdfBody" rows="4" placeholder="Auto-generated if left blank" style="width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; box-sizing: border-box; resize: vertical;"></textarea>
                    </div>
                    <div id="emailPdfAgencyFields">
                        <div style="margin-bottom: 14px;">
                            <label style="display: block; font-weight: 600; color: #374151; margin-bottom: 4px; font-size: 0.9rem;">Agency Name</label>
                            <input type="text" id="emailPdfAgencyName" placeholder="Optional" style="width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; box-sizing: border-box;">
                        </div>
                        <div style="margin-bottom: 14px;">
                            <label style="display: block; font-weight: 600; color: #374151; margin-bottom: 4px; font-size: 0.9rem;">Agency Website</label>
                            <input type="text" id="emailPdfAgencyWebsite" placeholder="Optional" style="width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; box-sizing: border-box;">
                        </div>
                    </div>
                    <button id="sendEmailPdfBtn" onclick="submitEmailPdfForm()" style="width: 100%; padding: 14px; font-size: 1rem; background: linear-gradient(135deg, #059669 0%, #10b981 100%); border: none; color: white; border-radius: 10px; cursor: pointer; font-weight: 700; transition: all 0.3s ease;">
                        Generate & Send Email
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);

    document.getElementById('emailPdfType').addEventListener('change', function() {
        const agencyFields = document.getElementById('emailPdfAgencyFields');
        agencyFields.style.display = this.value === 'client' ? 'block' : 'none';
    });
}

function closeEmailPdfForm() {
    const modal = document.getElementById('emailPdfFormModal');
    if (modal) modal.remove();
}

async function submitEmailPdfForm() {
    if (!currentScoreBreakdown || !currentScoreBreakdown.lead_id) {
        alert('No lead selected.');
        return;
    }

    const leadId = currentScoreBreakdown.lead_id;
    const reportType = document.getElementById('emailPdfType').value;
    const subject = document.getElementById('emailPdfSubject').value.trim();
    const body = document.getElementById('emailPdfBody').value.trim();
    const agencyName = document.getElementById('emailPdfAgencyName')?.value.trim() || '';
    const agencyWebsite = document.getElementById('emailPdfAgencyWebsite')?.value.trim() || '';

    const btn = document.getElementById('sendEmailPdfBtn');
    const origText = btn.innerHTML;
    btn.innerHTML = '<span style="display: inline-flex; align-items: center; gap: 8px;"><svg width="18" height="18" viewBox="0 0 24 24" style="animation: spin 1s linear infinite;"><style>@keyframes spin{to{transform:rotate(360deg)}}</style><circle cx="12" cy="12" r="10" stroke="white" stroke-width="3" fill="none" stroke-dasharray="31.4" stroke-dashoffset="10"/></svg> Sending...</span>';
    btn.disabled = true;

    try {
        const payload = { type: reportType };
        if (subject) payload.subject = subject;
        if (body) payload.body = `<html><body>${body.replace(/\n/g, '<br>')}</body></html>`;
        if (reportType === 'client') {
            if (agencyName) payload.agency_name = agencyName;
            if (agencyWebsite) payload.agency_website = agencyWebsite;
        }

        const response = await fetch(`/api/leads/${leadId}/report/email`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || err.error || 'Failed to send email');
        }

        const data = await response.json();
        closeEmailPdfForm();
        alert(`PDF report emailed successfully via ${data.provider || 'your email provider'}!`);
        loadLeads();
    } catch (error) {
        console.error('Email PDF error:', error);
        alert('Error sending PDF email: ' + error.message);
    } finally {
        btn.innerHTML = origText;
        btn.disabled = false;
    }
}

function showRescoreConfirmModal() {
    const leadCount = currentLeads.length;
    const modalHtml = `
        <div id="rescoreConfirmModal" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        ">
            <div style="
                background: white;
                padding: 24px;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                max-width: 420px;
                width: 90%;
            ">
                <h3 style="margin: 0 0 16px 0; color: #333;">Re-Score All Leads</h3>
                <p style="color: #666; margin-bottom: 16px; line-height: 1.5;">
                    This will re-analyze all <strong>${leadCount}</strong> leads with AI and generate detailed scoring breakdowns.
                </p>
                <p style="color: #888; font-size: 0.9rem; margin-bottom: 16px;">
                    This may take a minute depending on the number of leads.
                </p>
                <div style="display: flex; gap: 12px; margin-top: 16px; justify-content: flex-end;">
                    <button onclick="document.getElementById('rescoreConfirmModal').remove()" style="
                        padding: 10px 20px;
                        border: 1px solid #ddd;
                        background: white;
                        color: #333;
                        border-radius: 8px;
                        cursor: pointer;
                        font-size: 0.95rem;
                    ">Cancel</button>
                    <button onclick="confirmReScoreLeads()" style="
                        padding: 10px 20px;
                        background: linear-gradient(135deg, #4a6cf7 0%, #3b5ce5 100%);
                        color: white;
                        border: none;
                        border-radius: 8px;
                        cursor: pointer;
                        font-weight: 500;
                        font-size: 0.95rem;
                    ">Re-Score Now</button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

async function reScoreLeads() {
    if (currentLeads.length === 0) {
        showStatus('leadsStatus', 'No leads to score. Please search for leads first.', 'error');
        return;
    }
    
    showRescoreConfirmModal();
}

async function confirmReScoreLeads() {
    document.getElementById('rescoreConfirmModal').remove();
    
    showStatus('leadsStatus', 'Re-scoring all leads with AI...', 'info');
    
    try {
        const response = await fetch('/api/score-leads', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showStatus('leadsStatus', `✓ Re-scored ${data.count} leads with detailed breakdowns!`, 'success');
            await loadLeads();
            setTimeout(() => showStatus('leadsStatus', '', ''), 5000);
        } else {
            showStatus('leadsStatus', `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('leadsStatus', `Error: ${error.message}`, 'error');
    }
}

// Progress bar functions
function showProgressModal() {
    const modal = document.getElementById('campaignProgressModal');
    modal.style.display = 'block';
    resetProgressBar();
}

function closeProgressModal() {
    const modal = document.getElementById('campaignProgressModal');
    modal.style.display = 'none';
}

function resetProgressBar() {
    document.getElementById('progressFill').style.width = '0%';
    document.querySelectorAll('.progress-stage').forEach(stage => {
        stage.classList.remove('active', 'completed');
    });
    document.getElementById('progressStatus').textContent = '';
}

function updateProgress(stage, statusText) {
    // stage: 1, 2, or 3
    const progressFill = document.getElementById('progressFill');
    const progressStatus = document.getElementById('progressStatus');
    
    // Update progress bar width
    const widths = { 1: '33%', 2: '66%', 3: '100%' };
    progressFill.style.width = widths[stage] || '0%';
    
    // Update status text
    progressStatus.textContent = statusText || '';
    
    // Update stage states
    for (let i = 1; i <= 3; i++) {
        const stageElement = document.getElementById(`stage${i}`);
        if (i < stage) {
            stageElement.classList.remove('active');
            stageElement.classList.add('completed');
        } else if (i === stage) {
            stageElement.classList.remove('completed');
            stageElement.classList.add('active');
        } else {
            stageElement.classList.remove('active', 'completed');
        }
    }
}

function updateProgressWithDetail(stage, baseText, current, total) {
    const progressFill = document.getElementById('progressFill');
    const progressStatus = document.getElementById('progressStatus');
    
    // Calculate progress within stage 3 (scoring phase)
    // Stage 3 takes the bar from 66% to 100%
    if (stage === 3 && total > 0) {
        const stageProgress = current / total;
        const overallProgress = 66 + (34 * stageProgress);
        progressFill.style.width = `${overallProgress}%`;
    } else {
        const widths = { 1: '33%', 2: '66%', 3: '100%' };
        progressFill.style.width = widths[stage] || '0%';
    }
    
    // Show detailed count
    progressStatus.textContent = `${baseText} (${current}/${total})`;
    
    // Update stage states
    for (let i = 1; i <= 3; i++) {
        const stageElement = document.getElementById(`stage${i}`);
        if (i < stage) {
            stageElement.classList.remove('active');
            stageElement.classList.add('completed');
        } else if (i === stage) {
            stageElement.classList.remove('completed');
            stageElement.classList.add('active');
        } else {
            stageElement.classList.remove('active', 'completed');
        }
    }
}

// Sorting helper function
function getSortedLeads(leads) {
    if (!sortConfig.field) {
        return leads;
    }
    
    const sorted = [...leads].sort((a, b) => {
        let comparison = 0;
        
        switch (sortConfig.field) {
            case 'name':
                comparison = a.name.localeCompare(b.name);
                break;
            
            case 'email':
                const aHasEmail = a.email && a.email.trim() !== '';
                const bHasEmail = b.email && b.email.trim() !== '';
                if (aHasEmail && !bHasEmail) comparison = -1;
                else if (!aHasEmail && bHasEmail) comparison = 1;
                else comparison = 0;
                break;
            
            case 'score':
                comparison = (a.score || 0) - (b.score || 0);
                break;
            
            case 'website':
                const aWebsite = a.score_reasoning?.website_quality?.score ?? -1;
                const bWebsite = b.score_reasoning?.website_quality?.score ?? -1;
                comparison = aWebsite - bWebsite;
                break;
            
            case 'presence':
                const aPresence = a.score_reasoning?.digital_presence?.score ?? -1;
                const bPresence = b.score_reasoning?.digital_presence?.score ?? -1;
                comparison = aPresence - bPresence;
                break;
            
            case 'automation':
                const aAutomation = a.score_reasoning?.automation_opportunity?.score ?? -1;
                const bAutomation = b.score_reasoning?.automation_opportunity?.score ?? -1;
                comparison = aAutomation - bAutomation;
                break;
            
            case 'stage':
                const aOrder = STAGE_ORDER[a.stage] || 0;
                const bOrder = STAGE_ORDER[b.stage] || 0;
                comparison = aOrder - bOrder;
                break;
        }
        
        return sortConfig.direction === 'asc' ? comparison : -comparison;
    });
    
    return sorted;
}

// Sort by column (called when header is clicked)
function sortByColumn(field) {
    if (sortConfig.field === field) {
        // Toggle direction if same column
        sortConfig.direction = sortConfig.direction === 'asc' ? 'desc' : 'asc';
    } else {
        // New column, default to ascending
        sortConfig.field = field;
        sortConfig.direction = 'asc';
    }
    
    renderLeadsTable();
}

// Update sort indicators in table headers
function updateSortIndicators() {
    const headers = {
        'name': document.getElementById('sortName'),
        'email': document.getElementById('sortEmail'),
        'score': document.getElementById('sortScore'),
        'website': document.getElementById('sortWebsite'),
        'presence': document.getElementById('sortPresence'),
        'automation': document.getElementById('sortAutomation'),
        'stage': document.getElementById('sortStage')
    };
    
    // Clear all indicators
    Object.values(headers).forEach(header => {
        if (header) {
            header.className = 'sort-indicator';
        }
    });
    
    // Set active indicator
    if (sortConfig.field && headers[sortConfig.field]) {
        const indicator = headers[sortConfig.field];
        indicator.className = sortConfig.direction === 'asc' ? 'sort-indicator sort-asc' : 'sort-indicator sort-desc';
    }
}

// Compose email using score breakdown analysis
function composeEmailFromScore() {
    if (!currentScoreBreakdown) {
        alert('No score breakdown available');
        return;
    }
    
    const { lead_name, lead_id, score, reasoning } = currentScoreBreakdown;
    
    // Find the full lead data
    const lead = currentLeads.find(l => l.id === lead_id);
    if (!lead) {
        alert('Lead not found');
        return;
    }
    
    // Check if lead has email
    if (!lead.email || lead.email.trim() === '') {
        alert('This lead does not have an email address. Please add one first.');
        return;
    }
    
    // Generate personalized subject
    const subject = `${lead_name} - Opportunity to enhance your digital presence`;
    
    // Extract location for personalization (if available)
    const location = lead.address ? lead.address.split(',').pop().trim() : 'your area';
    
    // Generate personalized body based on score breakdown
    let body = `Hi ${lead_name} team,\n\n`;
    body += `I was analyzing local businesses in ${location} and came across your company. Based on my research, I identified both strengths and opportunities where AI and modern digital solutions could help you grow:\n\n`;
    
    // Add strengths from sales report
    const salesReport = reasoning?.sales_report;
    if (salesReport?.strengths && salesReport.strengths.length > 0) {
        body += `✅ What You're Doing Well:\n`;
        salesReport.strengths.slice(0, 3).forEach(s => {
            body += `• ${s}\n`;
        });
        body += `\n`;
    }
    
    // Add weaknesses/areas for improvement from sales report
    if (salesReport?.weaknesses && salesReport.weaknesses.length > 0) {
        body += `🔧 Opportunities for Improvement:\n`;
        salesReport.weaknesses.slice(0, 3).forEach(w => {
            body += `• ${w}\n`;
        });
        body += `\n`;
    }
    
    // Add specific sales opportunities
    if (salesReport?.sales_opportunities && salesReport.sales_opportunities.length > 0) {
        body += `💡 How We Can Help:\n`;
        salesReport.sales_opportunities.slice(0, 3).forEach(o => {
            body += `• ${o}\n`;
        });
        body += `\n`;
    }
    
    // Fallback if no sales report available - use component rationales
    if (!salesReport || (!salesReport.strengths && !salesReport.weaknesses && !salesReport.sales_opportunities)) {
        const components = [
            { name: 'Website & Online Presence', data: reasoning?.website_quality },
            { name: 'Digital Reputation & Visibility', data: reasoning?.digital_presence },
            { name: 'Automation & Efficiency', data: reasoning?.automation_opportunity }
        ];
        
        let hasInsights = false;
        components.forEach(component => {
            if (component.data && component.data.rationale) {
                body += `📌 ${component.name}:\n${component.data.rationale}\n\n`;
                hasInsights = true;
            }
        });
        
        if (!hasInsights) {
            body += `Based on my analysis, your business has significant potential for digital transformation and AI-powered improvements. I'd love to share specific recommendations tailored to your needs.\n\n`;
        }
    }
    
    // Add hybrid score breakdown
    body += `Hybrid Score: ${score}/100\n\n`;
    
    // Add summary if available
    if (reasoning?.summary) {
        body += `${reasoning.summary}\n\n`;
    }
    
    body += `I'd love to discuss how we can help you implement these improvements. Would you be open to a brief 15-minute call this week?\n\n`;
    body += `Best regards,\n[Your Name]`;
    
    // Close the modal
    closeScoreBreakdown();
    
    // Navigate to Email page
    showPage('email');
    
    // Pre-fill the email composer
    setTimeout(() => {
        document.getElementById('subjectTemplate').value = subject;
        document.getElementById('bodyTemplate').value = body;
        
        // Show a status message
        showStatus('emailStatus', '✓ Email drafted based on AI analysis! Review and customize before sending.', 'success');
        setTimeout(() => showStatus('emailStatus', '', ''), 5000);
    }, 100);
}

async function loadOAuthStatus() {
    try {
        const response = await fetch('/api/oauth/status');
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('gmailOAuthStatus').textContent = data.gmail_configured ? '✓ Configured' : 'Not configured';
            document.getElementById('gmailOAuthStatus').style.color = data.gmail_configured ? '#10b981' : '#b0b0b0';
            
            document.getElementById('outlookOAuthStatus').textContent = data.outlook_configured ? '✓ Configured' : 'Not configured';
            document.getElementById('outlookOAuthStatus').style.color = data.outlook_configured ? '#10b981' : '#b0b0b0';
        }
    } catch (error) {
        console.error('Error loading OAuth status:', error);
    }
}

// Email Signature Functions
async function loadEmailSignature() {
    try {
        const response = await fetch('/api/email-signature');
        if (response.ok) {
            const data = await response.json();
            document.getElementById('sigFullName').value = data.full_name || '';
            document.getElementById('sigPosition').value = data.position || '';
            document.getElementById('sigCompanyName').value = data.company_name || '';
            document.getElementById('sigPhone').value = data.phone || '';
            document.getElementById('sigWebsite').value = data.website || '';
            document.getElementById('sigLogoUrl').value = data.logo_url || '';
            document.getElementById('sigDisclaimer').value = data.disclaimer || '';
            document.getElementById('sigCustom').value = data.custom_signature || '';
            document.getElementById('sigUseCustom').checked = data.use_custom || false;
            
            // Show logo preview if exists
            if (data.logo_url) {
                showLogoPreview(data.logo_url);
            }
            
            toggleCustomSignature();
            updateSignaturePreview();
            
            // Load saved base pitch
            if (data.base_pitch) {
                document.getElementById('basePitch').value = data.base_pitch;
            }
        }
    } catch (error) {
        console.error('Error loading email signature:', error);
    }
}

function toggleCustomSignature() {
    const useCustom = document.getElementById('sigUseCustom').checked;
    document.getElementById('customSignatureSection').style.display = useCustom ? 'block' : 'none';
    updateSignaturePreview();
}

async function handleLogoUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    if (file.size > 2 * 1024 * 1024) {
        showStatus('signatureStatus', '✗ Logo file must be under 2MB', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const uploadArea = document.getElementById('logoUploadArea');
        uploadArea.style.opacity = '0.5';
        uploadArea.style.pointerEvents = 'none';
        
        const response = await fetch('/api/upload-logo', {
            method: 'POST',
            body: formData
        });
        
        uploadArea.style.opacity = '1';
        uploadArea.style.pointerEvents = 'auto';
        
        if (response.ok) {
            const data = await response.json();
            document.getElementById('sigLogoUrl').value = data.url;
            showLogoPreview(data.url);
            updateSignaturePreview();
            showStatus('signatureStatus', '✓ Logo uploaded! Remember to save your signature.', 'success');
        } else {
            const error = await response.json();
            showStatus('signatureStatus', `✗ ${error.detail || 'Failed to upload logo'}`, 'error');
        }
    } catch (error) {
        showStatus('signatureStatus', `✗ Error uploading logo: ${error.message}`, 'error');
    }
}

function showLogoPreview(url) {
    document.getElementById('logoPreviewImg').src = url;
    document.getElementById('logoPreviewContainer').style.display = 'block';
    document.getElementById('logoPlaceholder').style.display = 'none';
    document.getElementById('removeLogoBtn').style.display = 'inline-block';
    document.getElementById('logoUploadArea').style.borderColor = '#8b5cf6';
}

function removeLogo() {
    document.getElementById('sigLogoUrl').value = '';
    document.getElementById('sigLogoFile').value = '';
    document.getElementById('logoPreviewContainer').style.display = 'none';
    document.getElementById('logoPlaceholder').style.display = 'block';
    document.getElementById('removeLogoBtn').style.display = 'none';
    document.getElementById('logoUploadArea').style.borderColor = '#d1d5db';
    updateSignaturePreview();
}

function updateSignaturePreview() {
    const useCustom = document.getElementById('sigUseCustom').checked;
    const previewEl = document.getElementById('signaturePreview');
    
    if (useCustom) {
        const custom = document.getElementById('sigCustom').value;
        previewEl.innerHTML = custom ? custom.replace(/\n/g, '<br>') : '<em style="color: #999;">Enter your custom signature above</em>';
    } else {
        const name = document.getElementById('sigFullName').value;
        const position = document.getElementById('sigPosition').value;
        const company = document.getElementById('sigCompanyName').value;
        const phone = document.getElementById('sigPhone').value;
        const website = document.getElementById('sigWebsite').value;
        const logoUrl = document.getElementById('sigLogoUrl').value;
        const disclaimer = document.getElementById('sigDisclaimer').value;
        
        if (!name && !company) {
            previewEl.innerHTML = '<em style="color: #999;">Fill in the fields above to see your signature preview</em>';
            return;
        }
        
        let html = '<div style="border-top: 2px solid #8b5cf6; padding-top: 15px; margin-top: 10px;">';
        if (logoUrl) {
            html += `<img src="${logoUrl}" alt="Logo" style="max-height: 50px; margin-bottom: 10px;" onerror="this.style.display='none'"><br>`;
        }
        if (name) html += `<strong style="color: #333; font-size: 15px;">${name}</strong><br>`;
        if (position) html += `<span style="color: #666;">${position}</span><br>`;
        if (company) html += `<span style="color: #8b5cf6; font-weight: 600;">${company}</span><br>`;
        if (phone) html += `<span style="color: #666;">📞 ${phone}</span><br>`;
        if (website) html += `<a href="${website}" style="color: #3b82f6; text-decoration: none;">🌐 ${website}</a><br>`;
        if (disclaimer) {
            html += `<p style="font-size: 11px; color: #999; margin-top: 15px; font-style: italic;">${disclaimer}</p>`;
        }
        html += '</div>';
        previewEl.innerHTML = html;
    }
}

async function saveEmailSignature() {
    const data = {
        full_name: document.getElementById('sigFullName').value,
        position: document.getElementById('sigPosition').value,
        company_name: document.getElementById('sigCompanyName').value,
        phone: document.getElementById('sigPhone').value,
        website: document.getElementById('sigWebsite').value,
        logo_url: document.getElementById('sigLogoUrl').value,
        disclaimer: document.getElementById('sigDisclaimer').value,
        custom_signature: document.getElementById('sigCustom').value,
        use_custom: document.getElementById('sigUseCustom').checked
    };
    
    try {
        const response = await fetch('/api/email-signature', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            showStatus('signatureStatus', '✓ Email signature saved successfully!', 'success');
            setTimeout(() => showStatus('signatureStatus', '', ''), 3000);
        } else {
            const error = await response.json();
            showStatus('signatureStatus', `✗ ${error.detail || 'Failed to save signature'}`, 'error');
        }
    } catch (error) {
        showStatus('signatureStatus', `✗ Error: ${error.message}`, 'error');
    }
}

// Get formatted signature for emails
function getEmailSignature() {
    const useCustom = document.getElementById('sigUseCustom')?.checked;
    
    if (useCustom) {
        return document.getElementById('sigCustom')?.value || '';
    }
    
    const name = document.getElementById('sigFullName')?.value || '';
    const position = document.getElementById('sigPosition')?.value || '';
    const company = document.getElementById('sigCompanyName')?.value || '';
    const phone = document.getElementById('sigPhone')?.value || '';
    const website = document.getElementById('sigWebsite')?.value || '';
    const disclaimer = document.getElementById('sigDisclaimer')?.value || '';
    
    if (!name && !company) return '';
    
    let sig = '\n\n--\n';
    if (name) sig += `${name}\n`;
    if (position) sig += `${position}\n`;
    if (company) sig += `${company}\n`;
    if (phone) sig += `Phone: ${phone}\n`;
    if (website) sig += `${website}\n`;
    if (disclaimer) sig += `\n${disclaimer}`;
    
    return sig;
}

// Add event listeners for live preview
document.addEventListener('DOMContentLoaded', function() {
    const sigFields = ['sigFullName', 'sigPosition', 'sigCompanyName', 'sigPhone', 'sigWebsite', 'sigLogoUrl', 'sigDisclaimer', 'sigCustom'];
    sigFields.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', updateSignaturePreview);
        }
    });
});

function toggleOAuthConfig() {
    const section = document.getElementById('oauthConfigSection');
    section.style.display = section.style.display === 'none' ? 'block' : 'none';
}

async function saveGmailOAuth() {
    const clientId = document.getElementById('gmailClientId').value.trim();
    const clientSecret = document.getElementById('gmailClientSecret').value.trim();
    const redirectUri = document.getElementById('gmailRedirectUri').value.trim();
    
    if (!clientId || !clientSecret || !redirectUri) {
        showStatus('oauthStatus', 'Please fill in all Gmail OAuth fields', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/oauth/gmail/configure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_id: clientId, client_secret: clientSecret, redirect_uri: redirectUri })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showStatus('oauthStatus', '✅ Gmail OAuth configured successfully!', 'success');
            document.getElementById('gmailClientSecret').value = '';
            loadOAuthStatus();
            setTimeout(() => showStatus('oauthStatus', '', ''), 5000);
        } else {
            showStatus('oauthStatus', `❌ Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('oauthStatus', `❌ Error: ${error.message}`, 'error');
    }
}

async function saveOutlookOAuth() {
    const clientId = document.getElementById('outlookClientId').value.trim();
    const clientSecret = document.getElementById('outlookClientSecret').value.trim();
    const redirectUri = document.getElementById('outlookRedirectUri').value.trim();
    
    if (!clientId || !clientSecret || !redirectUri) {
        showStatus('oauthStatus', 'Please fill in all Outlook OAuth fields', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/oauth/outlook/configure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_id: clientId, client_secret: clientSecret, redirect_uri: redirectUri })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showStatus('oauthStatus', '✅ Outlook OAuth configured successfully!', 'success');
            document.getElementById('outlookClientSecret').value = '';
            loadOAuthStatus();
            setTimeout(() => showStatus('oauthStatus', '', ''), 5000);
        } else {
            showStatus('oauthStatus', `❌ Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus('oauthStatus', `❌ Error: ${error.message}`, 'error');
    }
}

let userCredits = { balance: 0, total_purchased: 0, total_used: 0 };

async function loadCredits() {
    try {
        const response = await fetch('/api/credits');
        if (response.ok) {
            const data = await response.json();
            userCredits = data;
            updateCreditsDisplay();
        }
    } catch (error) {
        console.error('Error loading credits:', error);
    }
}

function updateCreditsDisplay() {
    const balanceEl = document.getElementById('creditsBalance');
    const modalBalanceEl = document.getElementById('modalCreditsBalance');
    const landingBalanceEl = document.getElementById('landingCreditsBalance');
    const navItem = document.getElementById('creditsNavItem');
    
    if (balanceEl) balanceEl.textContent = userCredits.balance;
    if (modalBalanceEl) modalBalanceEl.textContent = userCredits.balance;
    if (landingBalanceEl) landingBalanceEl.textContent = userCredits.balance;
    const onboardingBalanceEl = document.getElementById('onboardingCreditBalance');
    if (onboardingBalanceEl) onboardingBalanceEl.textContent = userCredits.balance;
    if (navItem && currentUser) navItem.style.display = 'block';
}

function showCreditsModal() {
    const modal = document.getElementById('creditsModal');
    modal.style.display = 'flex';
    loadCredits();
    loadTransactionHistory();
    loadPaymentHistory();
    loadFoundingMemberSlots();
}

function closeCreditsModal() {
    document.getElementById('creditsModal').style.display = 'none';
}

async function loadFoundingMemberSlots() {
    try {
        const res = await fetch('/api/founding-member-slots');
        if (res.ok) {
            const data = await res.json();
            const el = document.getElementById('modalFoundingSlots');
            const pkg = document.getElementById('foundingMemberPackage');
            if (el) {
                if (data.remaining <= 0) {
                    el.textContent = 'SOLD OUT';
                    if (pkg) { pkg.style.opacity = '0.5'; pkg.style.pointerEvents = 'none'; }
                } else {
                    el.textContent = data.remaining + ' spots left!';
                }
            }
        }
    } catch (e) { console.error(e); }
}

async function loadPaymentHistory() {
    try {
        const response = await fetch('/api/payments/history');
        if (response.ok) {
            const data = await response.json();
            renderPaymentHistory(data.payments);
        }
    } catch (error) {
        console.error('Error loading payment history:', error);
    }
}

function renderPaymentHistory(payments) {
    const container = document.getElementById('paymentHistory');
    if (!container) return;
    
    if (!payments || payments.length === 0) {
        container.innerHTML = '<p class="empty-state">No payments yet</p>';
        return;
    }
    
    container.innerHTML = payments.map(p => {
        const date = new Date(p.created_at).toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric'
        });
        const amount = '$' + (p.amount_cents / 100).toFixed(2);
        const statusColor = p.status === 'completed' ? '#22c55e' : p.status === 'pending' ? '#f59e0b' : '#ef4444';
        
        return `
            <div class="transaction-item">
                <div class="transaction-info">
                    <span class="transaction-desc">${p.plan_name} - ${p.credits_purchased} credits</span>
                    <span class="transaction-date">${date}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="color: ${statusColor}; font-size: 0.8rem; font-weight: 600; text-transform: uppercase;">${p.status}</span>
                    <span class="transaction-amount amount-negative">${amount}</span>
                </div>
            </div>
        `;
    }).join('');
}

async function loadTransactionHistory() {
    try {
        const response = await fetch('/api/credits/transactions');
        if (response.ok) {
            const data = await response.json();
            renderTransactionHistory(data.transactions);
        }
    } catch (error) {
        console.error('Error loading transaction history:', error);
    }
}

function renderTransactionHistory(transactions) {
    const container = document.getElementById('transactionHistory');
    
    if (!transactions || transactions.length === 0) {
        container.innerHTML = '<p class="empty-state">No transactions yet</p>';
        return;
    }
    
    container.innerHTML = transactions.map(t => {
        const isCredit = t.amount > 0;
        const amountClass = isCredit ? 'amount-positive' : 'amount-negative';
        const amountPrefix = isCredit ? '+' : '';
        const date = new Date(t.created_at).toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'
        });
        
        return `
            <div class="transaction-item">
                <div class="transaction-info">
                    <span class="transaction-desc">${t.description}</span>
                    <span class="transaction-date">${date}</span>
                </div>
                <div class="transaction-amount ${amountClass}">
                    ${amountPrefix}${t.amount}
                </div>
            </div>
        `;
    }).join('');
}

async function purchaseCredits(packageId, evt) {
    const clickedEl = evt ? evt.target.closest('.credit-package') || evt.target : null;
    const btn = clickedEl ? clickedEl.querySelector('.package-btn') || clickedEl : null;
    
    if (btn) {
        btn.disabled = true;
        btn.dataset.originalText = btn.textContent;
        btn.textContent = 'Redirecting...';
    }
    
    try {
        const response = await fetch('/api/create-checkout-session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plan_name: packageId })
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.url) {
                window.location.href = data.url;
            }
        } else {
            const error = await response.json();
            showToast(error.detail || 'Failed to start checkout', 'error');
            if (btn) { btn.disabled = false; btn.textContent = btn.dataset.originalText || 'Buy Now'; }
        }
    } catch (error) {
        showToast('Error connecting to payment system. Please try again.', 'error');
        if (btn) { btn.disabled = false; btn.textContent = btn.dataset.originalText || 'Buy Now'; }
    }
}

function checkPaymentStatus() {
    const urlParams = new URLSearchParams(window.location.search);
    const plan = urlParams.get('plan');
    
    if (plan) {
        setTimeout(() => {
            purchaseCredits(plan);
        }, 500);
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

// ============== ADMIN FUNCTIONS ==============

let isAdmin = false;

async function loadAdminUsers() {
    const tbody = document.getElementById('adminUsersBody');
    try {
        const response = await fetch('/api/admin/users');
        if (response.status === 403) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #ef4444;">Access denied. Admin privileges required.</td></tr>';
            return;
        }
        if (!response.ok) throw new Error('Failed to load users');
        
        const data = await response.json();
        
        if (data.users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #6b7280;">No users found</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.users.map(user => `
            <tr>
                <td>${user.email}</td>
                <td>${user.full_name || '-'}</td>
                <td><span style="font-weight: 600; color: #4a6cf7;">${user.credits.toLocaleString()}</span></td>
                <td>${user.is_admin ? '<span style="color: #8b5cf6; font-weight: 600;">Yes</span>' : 'No'}</td>
                <td>${user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}</td>
                <td>
                    <button onclick="showAddCreditsModal(${user.id}, '${user.email}')" class="btn-small" style="background: linear-gradient(135deg, #4a6cf7 0%, #6366f1 100%); color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; margin-right: 5px;">
                        + Credits
                    </button>
                    <button onclick="toggleUserAdmin(${user.id}, ${!user.is_admin})" class="btn-small" style="background: ${user.is_admin ? '#ef4444' : '#8b5cf6'}; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer;">
                        ${user.is_admin ? 'Remove Admin' : 'Make Admin'}
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #ef4444;">Error: ${error.message}</td></tr>`;
    }
}

function showAddCreditsModal(userId, email) {
    document.getElementById('addCreditsUserId').value = userId;
    document.getElementById('addCreditsUserEmail').textContent = email;
    document.getElementById('addCreditsAmount').value = 100;
    document.getElementById('addCreditsReason').value = 'Admin credit adjustment';
    document.getElementById('addCreditsModal').style.display = 'flex';
}

function closeAddCreditsModal() {
    document.getElementById('addCreditsModal').style.display = 'none';
}

async function confirmAddCredits() {
    const userId = parseInt(document.getElementById('addCreditsUserId').value);
    const amount = parseInt(document.getElementById('addCreditsAmount').value);
    const reason = document.getElementById('addCreditsReason').value || 'Admin credit adjustment';
    
    if (!amount || amount <= 0) {
        showStatus('adminStatus', 'Please enter a valid amount', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/admin/credits/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, amount: amount, reason: reason })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            closeAddCreditsModal();
            showStatus('adminStatus', data.message, 'success');
            loadAdminUsers();
        } else {
            showStatus('adminStatus', data.detail || 'Failed to add credits', 'error');
        }
    } catch (error) {
        showStatus('adminStatus', 'Error: ' + error.message, 'error');
    }
}

async function toggleUserAdmin(userId, makeAdmin) {
    const action = makeAdmin ? 'grant admin to' : 'remove admin from';
    if (!confirm(`Are you sure you want to ${action} this user?`)) return;
    
    try {
        const response = await fetch('/api/admin/toggle-admin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, is_admin: makeAdmin })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showStatus('adminStatus', data.message, 'success');
            loadAdminUsers();
        } else {
            showStatus('adminStatus', data.detail || 'Failed to update admin status', 'error');
        }
    } catch (error) {
        showStatus('adminStatus', 'Error: ' + error.message, 'error');
    }
}

function checkAdminAccess(userData) {
    isAdmin = userData.user.is_admin || false;
    const adminNavItem = document.getElementById('adminNavItem');
    if (adminNavItem) {
        adminNavItem.style.display = isAdmin ? 'block' : 'none';
    }
}

// Override showPage to load admin data
const originalShowPage = showPage;
showPage = function(pageName) {
    originalShowPage(pageName);
    if (pageName === 'admin' && isAdmin) {
        loadAdminUsers();
    }
};

document.addEventListener('DOMContentLoaded', () => {
    checkPaymentStatus();
    loadWaitlistCount();
});


async function loadWaitlistCount() {
    try {
        const response = await fetch('/api/waitlist/count');
        if (!response.ok) return;
        const data = await response.json();

        const counter = document.getElementById('waitlistCounter');
        const urgencyText = document.getElementById('waitlistUrgencyText');
        const socialProof = document.getElementById('waitlistSocialProof');

        if (counter && data.free_spots_remaining > 0) {
            counter.textContent = `${data.free_spots_remaining} of 100 spots remaining`;
        } else if (counter) {
            counter.textContent = 'Founding member spots full';
        }

        if (urgencyText && data.free_spots_remaining <= 0) {
            urgencyText.textContent = 'Founding member spots full — join for priority access';
        }

        if (socialProof && data.total > 0) {
            socialProof.textContent = `Join ${data.total} others already on the waitlist`;
        }
    } catch (e) {
        console.error('Error loading waitlist count:', e);
    }
}

async function submitFreeWaitlist(event) {
    event.preventDefault();
    const btn = document.getElementById('waitlistFreeBtn');
    const email = document.getElementById('waitlistFreeEmail').value.trim();
    const name = document.getElementById('waitlistFreeName').value.trim();
    const source = document.getElementById('waitlistFreeSource').value;

    if (!email) return;

    btn.disabled = true;
    btn.innerHTML = 'Joining...';

    try {
        const response = await fetch('/api/waitlist/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: email,
                name: name || null,
                referral_source: source || null
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            window.location.href = `/waitlist/thankyou?email=${encodeURIComponent(email)}`;
        } else {
            showToast(data.detail || 'Something went wrong. Please try again.', 'error');
            btn.disabled = false;
            btn.innerHTML = 'Join the Waitlist <span class="btn-arrow">&rarr;</span>';
        }
    } catch (e) {
        showToast('Network error. Please try again.', 'error');
        btn.disabled = false;
        btn.innerHTML = 'Join the Waitlist <span class="btn-arrow">&rarr;</span>';
    }
}

async function submitFoundingWaitlist(event) {
    event.preventDefault();
    const btn = document.getElementById('waitlistFoundingBtn');
    const email = document.getElementById('waitlistFoundingEmail').value.trim();
    const name = document.getElementById('waitlistFoundingName').value.trim();
    const source = document.getElementById('waitlistFoundingSource').value;
    const plan = document.querySelector('input[name="foundingPlan"]:checked')?.value;

    if (!email || !plan) {
        showToast('Please enter your email and select a plan.', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = 'Processing...';

    try {
        const response = await fetch('/api/waitlist/founding', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: email,
                name: name || null,
                referral_source: source || null,
                plan: plan
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            if (data.checkout_url) {
                window.location.href = data.checkout_url;
            } else if (data.duplicate) {
                showToast(data.message, 'info');
                btn.disabled = false;
                btn.innerHTML = 'Pre-Order Now <span class="btn-arrow">&rarr;</span>';
            }
        } else {
            showToast(data.detail || 'Something went wrong. Please try again.', 'error');
            btn.disabled = false;
            btn.innerHTML = 'Pre-Order Now <span class="btn-arrow">&rarr;</span>';
        }
    } catch (e) {
        showToast('Network error. Please try again.', 'error');
        btn.disabled = false;
        btn.innerHTML = 'Pre-Order Now <span class="btn-arrow">&rarr;</span>';
    }
}


function openCsvImportModal() {
    resetCsvUpload();
    document.getElementById('csvImportModal').style.display = 'flex';
}

function closeCsvImportModal() {
    document.getElementById('csvImportModal').style.display = 'none';
    csvImportFile = null;
    csvImportParsedData = null;
}

function resetCsvUpload() {
    document.getElementById('csvUploadView').style.display = '';
    document.getElementById('csvPreviewView').style.display = 'none';
    document.getElementById('csvFileError').style.display = 'none';
    document.getElementById('csvFileInput').value = '';
    csvImportFile = null;
    csvImportParsedData = null;
}

function downloadCsvTemplate() {
    window.location.href = '/api/leads/csv-template';
}

function handleCsvFileSelect(file) {
    if (!file) return;
    const errorEl = document.getElementById('csvFileError');

    if (!file.name.toLowerCase().endsWith('.csv')) {
        errorEl.textContent = "Please select a .csv file.";
        errorEl.style.display = '';
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        errorEl.textContent = "File is too large (max 10MB).";
        errorEl.style.display = '';
        return;
    }

    errorEl.style.display = 'none';
    csvImportFile = file;

    const reader = new FileReader();
    reader.onload = function(e) {
        parseCsvPreview(e.target.result);
    };
    reader.readAsText(file);
}

function parseCsvPreview(text) {
    const errorEl = document.getElementById('csvFileError');
    const lines = text.trim().split('\n');
    if (lines.length < 2) {
        errorEl.textContent = "No data found in CSV.";
        errorEl.style.display = '';
        return;
    }

    const headerLine = lines[0];
    const headers = headerLine.split(',').map(h => h.trim().replace(/^"|"$/g, '').toLowerCase());

    if (!headers.includes('website_url')) {
        errorEl.textContent = "This doesn't match the LeadBlitz template. Please download the template and use the correct format.";
        errorEl.style.display = '';
        return;
    }

    const dataRows = [];
    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        const cols = parseSimpleCsvLine(line);
        const row = {};
        headers.forEach((h, idx) => { row[h] = (cols[idx] || '').trim(); });
        dataRows.push(row);
    }

    if (dataRows.length === 0) {
        errorEl.textContent = "No data rows found in CSV.";
        errorEl.style.display = '';
        return;
    }

    if (dataRows.length > 1000) {
        errorEl.textContent = "Maximum 1000 leads per import. Please split your file.";
        errorEl.style.display = '';
        return;
    }

    csvImportParsedData = dataRows;

    const thead = document.getElementById('csvPreviewHead');
    const tbody = document.getElementById('csvPreviewBody');
    thead.innerHTML = '<tr>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr>';

    const previewRows = dataRows.slice(0, 5);
    tbody.innerHTML = previewRows.map(row =>
        '<tr>' + headers.map(h => `<td>${escapeHtml(row[h] || '')}</td>`).join('') + '</tr>'
    ).join('');

    if (dataRows.length > 5) {
        tbody.innerHTML += `<tr><td colspan="${headers.length}" style="text-align:center;color:#888;font-style:italic;">... and ${dataRows.length - 5} more rows</td></tr>`;
    }

    document.getElementById('csvPreviewSummary').textContent = `${dataRows.length} leads found. Estimated credits: up to ${dataRows.length}.`;
    document.getElementById('csvUploadView').style.display = 'none';
    document.getElementById('csvPreviewView').style.display = '';
}

function parseSimpleCsvLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
        const ch = line[i];
        if (ch === '"') {
            inQuotes = !inQuotes;
        } else if (ch === ',' && !inQuotes) {
            result.push(current);
            current = '';
        } else {
            current += ch;
        }
    }
    result.push(current);
    return result;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

async function submitCsvImport() {
    if (!csvImportFile) return;

    const btn = document.getElementById('csvImportBtn');
    btn.disabled = true;
    btn.textContent = 'Importing...';

    try {
        const formData = new FormData();
        formData.append('file', csvImportFile);

        const response = await fetch('/api/leads/import-csv', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        const data = await response.json();

        if (!response.ok) {
            const detail = data.detail || data;
            const msg = typeof detail === 'object' ? detail.message : detail;
            showToast(msg || 'Import failed', 'error', 6000);
            btn.disabled = false;
            btn.textContent = 'Import & Score';
            return;
        }

        closeCsvImportModal();
        showToast(data.message || `Import started - scoring ${data.summary.credits_to_use} websites...`, 'info', 5000);

        if (data.summary.credits_to_use > 0) {
            startCsvProgressPolling(data.import_id, data.summary.to_score);
        }

        loadLeads();
        loadCredits();
    } catch (e) {
        showToast('Network error during import. Please try again.', 'error');
        btn.disabled = false;
        btn.textContent = 'Import & Score';
    }
}

function startCsvProgressPolling(importId, total) {
    const progressEl = document.getElementById('csvImportProgress');
    const barEl = document.getElementById('csvProgressBar');
    const labelEl = document.getElementById('csvProgressLabel');
    const countEl = document.getElementById('csvProgressCount');

    progressEl.style.display = '';
    barEl.style.width = '0%';
    labelEl.textContent = 'Scoring...';
    countEl.textContent = `0/${total} complete`;

    if (csvImportPollingId) clearInterval(csvImportPollingId);

    csvImportPollingId = setInterval(async () => {
        try {
            const resp = await fetch(`/api/leads/import-status/${importId}`, { credentials: 'include' });
            if (!resp.ok) { clearInterval(csvImportPollingId); return; }
            const status = await resp.json();

            const done = status.scored + status.unreachable;
            const pct = total > 0 ? Math.round((done / total) * 100) : 0;
            barEl.style.width = pct + '%';
            countEl.textContent = `${done}/${total} complete`;

            if (status.status === 'completed' || status.status === 'partial') {
                clearInterval(csvImportPollingId);
                csvImportPollingId = null;

                labelEl.textContent = 'Import complete!';
                barEl.style.width = '100%';

                let msg = `Import complete - ${status.scored} scored`;
                if (status.unreachable > 0) msg += `, ${status.unreachable} unreachable`;
                if (status.pending_credits > 0) {
                    showToast(`Scored ${status.scored} of ${total} leads. Upgrade to score the remaining ${status.pending_credits}.`, 'info', 8000);
                } else {
                    showToast(msg, 'success', 5000);
                }

                loadLeads();
                loadCredits();

                setTimeout(() => { progressEl.style.display = 'none'; }, 5000);
            }
        } catch (e) {
            console.error('Progress polling error:', e);
        }
    }, 3000);
}

(function() {
    const dropZone = document.getElementById('csvDropZone');
    if (!dropZone) return;
    ['dragenter', 'dragover'].forEach(evt => {
        dropZone.addEventListener(evt, e => { e.preventDefault(); e.stopPropagation(); dropZone.classList.add('dragover'); });
    });
    ['dragleave', 'drop'].forEach(evt => {
        dropZone.addEventListener(evt, e => { e.preventDefault(); e.stopPropagation(); dropZone.classList.remove('dragover'); });
    });
    dropZone.addEventListener('drop', e => {
        const file = e.dataTransfer.files[0];
        if (file) handleCsvFileSelect(file);
    });
})();
