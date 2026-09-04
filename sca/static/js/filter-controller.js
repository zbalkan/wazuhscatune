/**
 * Filter Controller
 * Manages filtering and searching of checks
 */

class FilterController {
    constructor(checks, cardManager) {
        
        this.checks = checks;
        this.cardManager = cardManager;
        this.activeFilters = {
            status: ['accepted', 'exception', 'unreviewed'],
            searchText: '',
            impactSearchText: ''
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
        
        // General search
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
        
        // Impact search
        const impactSearchInput = document.getElementById('impact-search-input');
        if (impactSearchInput) {
            let debounceTimer;
            impactSearchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.handleImpactSearch(e.target.value);
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
    
    handleSearch(query) {
        this.activeFilters.searchText = query.toLowerCase();
        this.applyFilters();
    }
    
    handleImpactSearch(query) {
        this.activeFilters.impactSearchText = query.toLowerCase();
        this.applyFilters();
    }
    
    applyFilters() {
        
        const filteredChecks = this.getFilteredChecks();
        const filteredIds = filteredChecks.map(c => c.id);
        
        
        this.cardManager.filterCards(filteredIds);
    }
    
    getFilteredChecks() {
        const result = this.checks.filter(check => {
            // Status filter
            const checkStatus = this.getCheckStatus(check.id);
            if (!this.activeFilters.status.includes(checkStatus)) {
                return false;
            }
            
            // Impact search filter (text-based)
            if (this.activeFilters.impactSearchText) {
                const checkImpact = (check.impact || '').toLowerCase();
                if (!checkImpact.includes(this.activeFilters.impactSearchText)) {
                    return false;
                }
            }
            
            // General search filter
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
        
        return result;
    }
    
    getCheckStatus(checkId) {
        const decision = this.cardManager.decisions[checkId];
        if (!decision) {
            return 'unreviewed';
        }
        return decision.decision;
    }
    
    clearFilters() {
        // Reset status filters
        const statusCheckboxes = document.querySelectorAll('input[name="status"]');
        statusCheckboxes.forEach(cb => cb.checked = true);
        this.activeFilters.status = ['accepted', 'exception', 'unreviewed'];
        
        // Reset general search
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.value = '';
            this.activeFilters.searchText = '';
        }
        
        // Reset impact search
        const impactSearchInput = document.getElementById('impact-search-input');
        if (impactSearchInput) {
            impactSearchInput.value = '';
            this.activeFilters.impactSearchText = '';
        }
        
        this.applyFilters();
    }
}

// Make globally available
window.FilterController = FilterController;
