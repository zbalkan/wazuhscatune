/**
 * Filter Controller
 * Manages filtering and searching of checks
 */

class FilterController {
    constructor(checks, cardManager) {
        console.log('[FilterController] Initializing...');
        console.log('[FilterController] Checks count:', checks.length);
        
        this.checks = checks;
        this.cardManager = cardManager;
        this.activeFilters = {
            status: ['accepted', 'exception', 'unreviewed'],
            searchText: '',
            impactSearchText: ''
        };
        
        console.log('[FilterController] Initial filters:', this.activeFilters);
        
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
        console.log('[FilterController] Applying filters...');
        console.log('[FilterController] Active filters:', this.activeFilters);
        console.log('[FilterController] Total checks:', this.checks.length);
        
        const filteredChecks = this.getFilteredChecks();
        const filteredIds = filteredChecks.map(c => c.id);
        
        console.log('[FilterController] Filtered checks count:', filteredChecks.length);
        console.log('[FilterController] Filtered check IDs:', filteredIds);
        
        this.cardManager.filterCards(filteredIds);
    }
    
    getFilteredChecks() {
        let statusFiltered = 0;
        let impactSearchFiltered = 0;
        let searchFiltered = 0;
        
        const result = this.checks.filter(check => {
            // Status filter
            const checkStatus = this.getCheckStatus(check.id);
            if (!this.activeFilters.status.includes(checkStatus)) {
                statusFiltered++;
                return false;
            }
            
            // Impact search filter (text-based)
            if (this.activeFilters.impactSearchText) {
                const checkImpact = (check.impact || '').toLowerCase();
                if (!checkImpact.includes(this.activeFilters.impactSearchText)) {
                    impactSearchFiltered++;
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
                    searchFiltered++;
                    return false;
                }
            }
            
            return true;
        });
        
        console.log('[FilterController] Filter results:');
        console.log(`  - Filtered by status: ${statusFiltered}`);
        console.log(`  - Filtered by impact search: ${impactSearchFiltered}`);
        console.log(`  - Filtered by general search: ${searchFiltered}`);
        console.log(`  - Passed filters: ${result.length}`);
        
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
