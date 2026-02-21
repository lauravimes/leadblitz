/* ============================================
   MOBILE INTERACTIONS & FUNCTIONALITY
   Enhanced mobile UX for LeadBlitz
   ============================================ */

// Mobile navigation state
let mobileMenuOpen = false;
let lastScrollY = 0;
let ticking = false;

// Initialize mobile functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeMobileFeatures();
});

// Main mobile initialization function
function initializeMobileFeatures() {
    setupMobileNavigation();
    setupMobileDataViews();
    setupMobileModals();
    setupTouchInteractions();
    setupMobileScrollBehavior();
}

/* ============================================
   MOBILE NAVIGATION
   ============================================ */

function setupMobileNavigation() {
    // Create mobile menu toggle if it doesn't exist
    let mobileToggle = document.querySelector('.mobile-menu-toggle');
    if (!mobileToggle) {
        mobileToggle = createMobileMenuToggle();
    }
    
    // Set up mobile menu toggle event
    mobileToggle.addEventListener('click', toggleMobileMenu);
    
    // Close mobile menu when clicking outside
    document.addEventListener('click', function(e) {
        const navMenu = document.querySelector('.nav-menu');
        const mobileToggle = document.querySelector('.mobile-menu-toggle');
        
        if (mobileMenuOpen && navMenu && !navMenu.contains(e.target) && !mobileToggle.contains(e.target)) {
            closeMobileMenu();
        }
    });
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768 && mobileMenuOpen) {
            closeMobileMenu();
        }
    });
    
    // Prevent scroll when mobile menu is open
    function preventScroll(e) {
        if (mobileMenuOpen) {
            e.preventDefault();
        }
    }
    
    document.addEventListener('touchmove', preventScroll, { passive: false });
}

function createMobileMenuToggle() {
    const navContainer = document.querySelector('.nav-container');
    if (!navContainer) return;
    
    const toggle = document.createElement('button');
    toggle.className = 'mobile-menu-toggle';
    toggle.innerHTML = '<span></span><span></span><span></span>';
    toggle.setAttribute('aria-label', 'Toggle mobile menu');
    
    navContainer.appendChild(toggle);
    return toggle;
}

function toggleMobileMenu() {
    if (mobileMenuOpen) {
        closeMobileMenu();
    } else {
        openMobileMenu();
    }
}

function openMobileMenu() {
    const navMenu = document.querySelector('.nav-menu');
    const mobileToggle = document.querySelector('.mobile-menu-toggle');
    const body = document.body;
    
    if (navMenu && mobileToggle) {
        navMenu.classList.add('active');
        mobileToggle.classList.add('active');
        body.classList.add('mobile-menu-open');
        mobileMenuOpen = true;
        
        // Focus management for accessibility
        const firstMenuItem = navMenu.querySelector('a');
        if (firstMenuItem) {
            firstMenuItem.focus();
        }
        
        // Add escape key listener
        document.addEventListener('keydown', handleMobileMenuEscape);
    }
}

function closeMobileMenu() {
    const navMenu = document.querySelector('.nav-menu');
    const mobileToggle = document.querySelector('.mobile-menu-toggle');
    const body = document.body;
    
    if (navMenu && mobileToggle) {
        navMenu.classList.remove('active');
        mobileToggle.classList.remove('active');
        body.classList.remove('mobile-menu-open');
        mobileMenuOpen = false;
        
        // Remove escape key listener
        document.removeEventListener('keydown', handleMobileMenuEscape);
    }
}

function handleMobileMenuEscape(e) {
    if (e.key === 'Escape') {
        closeMobileMenu();
    }
}

/* ============================================
   MOBILE DATA VIEWS (Tables to Cards)
   ============================================ */

function setupMobileDataViews() {
    // Convert tables to mobile card views on small screens
    if (window.innerWidth <= 768) {
        convertTablesToCards();
    }
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth <= 768) {
            convertTablesToCards();
        } else {
            restoreOriginalTables();
        }
    });
}

function convertTablesToCards() {
    // Convert leads table
    const leadsTable = document.querySelector('.leads-table');
    if (leadsTable && !document.querySelector('.mobile-leads-cards')) {
        convertLeadsTableToCards(leadsTable);
    }
    
    // Convert campaigns table
    const campaignsTable = document.querySelector('.campaigns-table');
    if (campaignsTable && !document.querySelector('.mobile-campaigns-cards')) {
        convertCampaignsTableToCards(campaignsTable);
    }
}

function convertLeadsTableToCards(table) {
    const container = table.parentNode;
    const rows = table.querySelectorAll('tbody tr');
    
    if (rows.length === 0) return;
    
    const mobileContainer = document.createElement('div');
    mobileContainer.className = 'mobile-data-cards mobile-leads-cards';
    
    rows.forEach(row => {
        const card = createLeadCard(row);
        if (card) {
            mobileContainer.appendChild(card);
        }
    });
    
    // Insert mobile cards after the table
    container.insertBefore(mobileContainer, table.nextSibling);
}

function createLeadCard(row) {
    const cells = row.querySelectorAll('td');
    if (cells.length === 0) return null;
    
    const card = document.createElement('div');
    card.className = 'mobile-data-card';
    
    // Extract data from table cells (adjust indices based on your table structure)
    const businessName = cells[0]?.textContent?.trim() || 'Unknown Business';
    const score = cells[1]?.textContent?.trim() || '0';
    const address = cells[2]?.textContent?.trim() || '';
    const phone = cells[3]?.textContent?.trim() || '';
    const website = cells[4]?.textContent?.trim() || '';
    
    card.innerHTML = `
        <div class="mobile-card-header">
            <h4 class="mobile-card-title">${businessName}</h4>
            <div class="mobile-card-score">${score}</div>
        </div>
        <div class="mobile-card-details">
            <div class="mobile-card-detail">
                <strong>Address</strong>
                ${address || 'Not available'}
            </div>
            <div class="mobile-card-detail">
                <strong>Phone</strong>
                ${phone || 'Not available'}
            </div>
        </div>
        <div class="mobile-card-actions">
            <button class="btn btn-sm btn-primary" onclick="viewLeadDetails('${businessName}')">
                View Details
            </button>
            <button class="btn btn-sm btn-secondary" onclick="contactLead('${phone}')">
                Contact
            </button>
        </div>
    `;
    
    return card;
}

function convertCampaignsTableToCards(table) {
    const container = table.parentNode;
    const rows = table.querySelectorAll('tbody tr');
    
    if (rows.length === 0) return;
    
    const mobileContainer = document.createElement('div');
    mobileContainer.className = 'mobile-data-cards mobile-campaigns-cards';
    
    rows.forEach(row => {
        const card = createCampaignCard(row);
        if (card) {
            mobileContainer.appendChild(card);
        }
    });
    
    container.insertBefore(mobileContainer, table.nextSibling);
}

function createCampaignCard(row) {
    const cells = row.querySelectorAll('td');
    if (cells.length === 0) return null;
    
    const card = document.createElement('div');
    card.className = 'mobile-data-card';
    
    // Extract campaign data
    const name = cells[0]?.textContent?.trim() || 'Unnamed Campaign';
    const leads = cells[1]?.textContent?.trim() || '0';
    const sent = cells[2]?.textContent?.trim() || '0';
    const status = cells[3]?.textContent?.trim() || 'Unknown';
    
    card.innerHTML = `
        <div class="mobile-card-header">
            <h4 class="mobile-card-title">${name}</h4>
            <div class="mobile-card-score">${leads}</div>
        </div>
        <div class="mobile-card-details">
            <div class="mobile-card-detail">
                <strong>Sent</strong>
                ${sent}
            </div>
            <div class="mobile-card-detail">
                <strong>Status</strong>
                ${status}
            </div>
        </div>
        <div class="mobile-card-actions">
            <button class="btn btn-sm btn-primary" onclick="viewCampaign('${name}')">
                View Campaign
            </button>
            <button class="btn btn-sm btn-secondary" onclick="editCampaign('${name}')">
                Edit
            </button>
        </div>
    `;
    
    return card;
}

function restoreOriginalTables() {
    // Remove mobile card views on desktop
    const mobileCards = document.querySelectorAll('.mobile-data-cards');
    mobileCards.forEach(cards => cards.remove());
}

/* ============================================
   MOBILE MODAL ENHANCEMENTS
   ============================================ */

function setupMobileModals() {
    // Enhanced modal behavior for mobile
    const modals = document.querySelectorAll('.modal-overlay');
    
    modals.forEach(modal => {
        modal.addEventListener('touchstart', handleModalTouch);
        modal.addEventListener('touchmove', handleModalScroll);
    });
    
    // Add mobile-specific modal close handlers
    const closeButtons = document.querySelectorAll('.modal-close, .auth-close');
    closeButtons.forEach(btn => {
        btn.addEventListener('touchend', function(e) {
            e.preventDefault();
            this.click();
        });
    });
}

function handleModalTouch(e) {
    // Prevent background scroll when modal is open
    if (e.target === e.currentTarget) {
        e.preventDefault();
    }
}

function handleModalScroll(e) {
    const modal = e.currentTarget;
    const modalContent = modal.querySelector('.modal-content, .auth-modal-content, .tutorial-modal-content');
    
    if (modalContent && !modalContent.contains(e.target)) {
        e.preventDefault();
    }
}

/* ============================================
   TOUCH INTERACTIONS
   ============================================ */

function setupTouchInteractions() {
    // Add touch feedback to interactive elements
    const interactiveElements = document.querySelectorAll('button, .btn, a, .clickable');
    
    interactiveElements.forEach(element => {
        element.addEventListener('touchstart', addTouchFeedback);
        element.addEventListener('touchend', removeTouchFeedback);
        element.addEventListener('touchcancel', removeTouchFeedback);
    });
    
    // Setup swipe gestures for data cards
    setupSwipeGestures();
}

function addTouchFeedback(e) {
    const element = e.currentTarget;
    element.classList.add('touch-active');
}

function removeTouchFeedback(e) {
    const element = e.currentTarget;
    setTimeout(() => {
        element.classList.remove('touch-active');
    }, 150);
}

function setupSwipeGestures() {
    let startX, startY, currentX, currentY;
    let isSwipping = false;
    
    const cards = document.querySelectorAll('.mobile-data-card');
    
    cards.forEach(card => {
        card.addEventListener('touchstart', function(e) {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            isSwipping = false;
        });
        
        card.addEventListener('touchmove', function(e) {
            if (!startX || !startY) return;
            
            currentX = e.touches[0].clientX;
            currentY = e.touches[0].clientY;
            
            const diffX = Math.abs(currentX - startX);
            const diffY = Math.abs(currentY - startY);
            
            if (diffX > diffY && diffX > 30) {
                isSwipping = true;
                e.preventDefault();
                
                // Add swipe visual feedback
                const swipeDistance = currentX - startX;
                card.style.transform = `translateX(${swipeDistance * 0.3}px)`;
                card.style.opacity = Math.max(0.3, 1 - Math.abs(swipeDistance) / 200);
            }
        });
        
        card.addEventListener('touchend', function(e) {
            if (isSwipping && currentX && startX) {
                const swipeDistance = currentX - startX;
                const threshold = 100;
                
                if (Math.abs(swipeDistance) > threshold) {
                    // Swipe action triggered
                    handleCardSwipe(card, swipeDistance > 0 ? 'right' : 'left');
                } else {
                    // Return to original position
                    card.style.transform = '';
                    card.style.opacity = '';
                }
            } else {
                card.style.transform = '';
                card.style.opacity = '';
            }
            
            startX = null;
            startY = null;
            currentX = null;
            currentY = null;
            isSwipping = false;
        });
    });
}

function handleCardSwipe(card, direction) {
    // Implement swipe actions (e.g., delete, archive, etc.)
    if (direction === 'right') {
        // Swipe right action
        showMobileToast('Swipe right action');
    } else {
        // Swipe left action
        showMobileToast('Swipe left action');
    }
    
    // Reset card position
    setTimeout(() => {
        card.style.transform = '';
        card.style.opacity = '';
    }, 200);
}

/* ============================================
   MOBILE SCROLL BEHAVIOR
   ============================================ */

function setupMobileScrollBehavior() {
    let isScrolling = false;
    
    window.addEventListener('scroll', function() {
        if (!isScrolling) {
            window.requestAnimationFrame(function() {
                handleMobileScroll();
                isScrolling = false;
            });
            isScrolling = true;
        }
    });
}

function handleMobileScroll() {
    const currentScrollY = window.scrollY;
    const nav = document.querySelector('.top-nav');
    
    if (!nav) return;
    
    // Hide nav on scroll down, show on scroll up (mobile only)
    if (window.innerWidth <= 768) {
        if (currentScrollY > lastScrollY && currentScrollY > 100) {
            // Scrolling down
            nav.style.transform = 'translateY(-100%)';
        } else {
            // Scrolling up
            nav.style.transform = 'translateY(0)';
        }
    }
    
    lastScrollY = currentScrollY;
}

/* ============================================
   MOBILE UTILITIES
   ============================================ */

function showMobileToast(message, duration = 3000) {
    // Remove existing toast
    const existingToast = document.querySelector('.toast-mobile');
    if (existingToast) {
        existingToast.remove();
    }
    
    // Create new toast
    const toast = document.createElement('div');
    toast.className = 'toast-mobile';
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Auto remove after duration
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, duration);
}

function isMobileDevice() {
    return window.innerWidth <= 768;
}

function orientationChanged() {
    // Handle orientation changes
    setTimeout(() => {
        if (mobileMenuOpen) {
            closeMobileMenu();
        }
        convertTablesToCards();
    }, 100);
}

// Listen for orientation changes
window.addEventListener('orientationchange', orientationChanged);

/* ============================================
   MOBILE FORM ENHANCEMENTS
   ============================================ */

function enhanceMobileForms() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        // Add mobile-friendly validation
        const inputs = form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            // Add touch-friendly focus behavior
            input.addEventListener('focus', function() {
                this.classList.add('mobile-focused');
                
                // Scroll input into view on mobile
                if (isMobileDevice()) {
                    setTimeout(() => {
                        this.scrollIntoView({ 
                            behavior: 'smooth', 
                            block: 'center' 
                        });
                    }, 300);
                }
            });
            
            input.addEventListener('blur', function() {
                this.classList.remove('mobile-focused');
            });
        });
        
        // Prevent zoom on input focus (iOS Safari)
        const metaViewport = document.querySelector('meta[name="viewport"]');
        if (metaViewport) {
            inputs.forEach(input => {
                input.addEventListener('focus', () => {
                    metaViewport.setAttribute('content', 
                        'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0'
                    );
                });
                
                input.addEventListener('blur', () => {
                    metaViewport.setAttribute('content', 
                        'width=device-width, initial-scale=1.0'
                    );
                });
            });
        }
    });
}

// Initialize form enhancements when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhanceMobileForms);
} else {
    enhanceMobileForms();
}

/* ============================================
   MOBILE PERFORMANCE OPTIMIZATION
   ============================================ */

// Debounce function for performance
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

// Throttle function for scroll events
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Export functions for global use
window.mobileUtils = {
    showMobileToast,
    isMobileDevice,
    closeMobileMenu,
    openMobileMenu,
    debounce,
    throttle
};