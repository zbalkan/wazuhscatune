/**
 * Filter Controller
 * Manages filtering and searching of checks
 */

class FilterController {
    constructor(checks, cardManager) {
        this.checks = checks;
        this.cardManager = cardManager;
        this.activeFilters = {
            status: ['included', 'excluded', 'unreviewed'],
            impact: ['high', 'medium', 'low'],
            searchText: ''
        };
        
        this.initializeEventListeners();
        this.applyFilters();
    }
    
    initializeEventListeners() {
        // Status filters
        const statusCheckboxes = document.querySelectorAll('input[name="status"]');
        statusCheckboxes.forEach(cb => {
            cb.addEventListener('change', () => this.handleStatusFilter());
        });
        
        // Impact filters
        const impactCheckboxes = document.querySelectorAll('input[name="impact"]');
        impactCheckboxes.forEach(cb => {
            cb.addEventListener('change', () => this.handleImpactFilter());
        });
        
        // Search
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.handleSearch(e.target.value);
                }, 300);
            });
        }
        
        // Clear filters
        const clearBtn = document.getElementById('clear-filters-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearFilters());
        }
    }
    
    handleStatusFilter() {
        const statusCheckboxes = document.querySelectorAll('input[name="status"]:checked');
        this.activeFilters.status = Array.from(statusCheckboxes).map(cb => cb.value);
        this.applyFilters();
    }
    
    handleImpactFilter() {
        const impactCheckboxes = document.querySelectorAll('input[name="impact"]:checked');
        this.activeFilters.impact = Array.from(impactCheckboxes).map(cb => cb.value);
        this.applyFilters();
    }
    
    handleSearch(query) {
        this.activeFilters.searchText = query.toLowerCase();
        this.applyFilters();
    }
    
    applyFilters() {
        const filteredChecks = this.getFilteredChecks();
        const filteredIds = filteredChecks.map(c => c.id);
        this.cardManager.filterCards(filteredIds);
    }
    
    getFilteredChecks() {
        return this.checks.filter(check => {
            // Status filter
            const checkStatus = this.getCheckStatus(check.id);
            if (!this.activeFilters.status.includes(checkStatus)) {
                return false;
            }
            
            // Impact filter
            const checkImpact = (check.impact || '').toLowerCase();
            if (checkImpact && !this.activeFilters.impact.includes(checkImpact)) {
                return false;
            }
            
            // Search filter
            if (this.activeFilters.searchText) {
                const searchableText = [
                    check.id.toString(),
                    check.title,
                    check.description || '',
                    check.rationale || '',
                    check.remediation || ''
                ].join(' ').toLowerCase();
                
                if (!searchableText.includes(this.activeFilters.searchText)) {
                    return false;
                }
            }
            
            return true;
        });
    }
    
    getCheckStatus(checkId) {
        const decision = this.cardManager.decisions[checkId];
        if (!decision) {
            return 'unreviewed';
        }
        return decision.excluded ? 'excluded' : 'included';
    }
    
    clearFilters() {
        // Reset status filters
        const statusCheckboxes = document.querySelectorAll('input[name="status"]');
        statusCheckboxes.forEach(cb => cb.checked = true);
        this.activeFilters.status = ['included', 'excluded', 'unreviewed'];
        
        // Reset impact filters
        const impactCheckboxes = document.querySelectorAll('input[name="impact"]');
        impactCheckboxes.forEach(cb => cb.checked = true);
        this.activeFilters.impact = ['high', 'medium', 'low'];
        
        // Reset search
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.value = '';
            this.activeFilters.searchText = '';
        }
        
        this.applyFilters();
    }
}

// Make globally available
window.FilterController = FilterController;
