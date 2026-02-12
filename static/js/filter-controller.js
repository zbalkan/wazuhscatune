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
            status: ['included', 'excluded', 'unreviewed'],
            impact: ['high', 'medium', 'low'],
            searchText: ''
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
        let impactFiltered = 0;
        let searchFiltered = 0;
        
        const result = this.checks.filter(check => {
            // Status filter
            const checkStatus = this.getCheckStatus(check.id);
            if (!this.activeFilters.status.includes(checkStatus)) {
                statusFiltered++;
                return false;
            }
            
            // Impact filter - only apply to checks with recognized impact levels
            const checkImpact = (check.impact || '').toLowerCase().trim();
            const validImpactLevels = ['high', 'medium', 'low'];
            
            // Only filter if the check has a RECOGNIZED impact level
            // If impact is unrecognized or empty, let it pass through
            if (validImpactLevels.includes(checkImpact)) {
                // This check has a valid impact level - apply the filter
                if (!this.activeFilters.impact.includes(checkImpact)) {
                    impactFiltered++;
                    console.log(`[FilterController] Check ${check.id} filtered by impact: "${checkImpact}" not in`, this.activeFilters.impact);
                    return false;
                }
            } else {
                // Impact is unrecognized (e.g., long description text or empty)
                // Always pass through - don't filter based on impact
                console.log(`[FilterController] Check ${check.id} has non-standard impact, passing through: "${checkImpact.substring(0, 50)}..."`);
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
                    searchFiltered++;
                    return false;
                }
            }
            
            return true;
        });
        
        console.log('[FilterController] Filter results:');
        console.log(`  - Filtered by status: ${statusFiltered}`);
        console.log(`  - Filtered by impact: ${impactFiltered}`);
        console.log(`  - Filtered by search: ${searchFiltered}`);
        console.log(`  - Passed filters: ${result.length}`);
        
        // Sample some checks that were filtered by impact
        if (impactFiltered > 0 && impactFiltered < 10) {
            console.log('[FilterController] Sample impact values from checks:');
            this.checks.slice(0, 10).forEach(check => {
                const checkImpact = (check.impact || '').toLowerCase();
                console.log(`  Check ${check.id}: impact="${checkImpact}" (length: ${checkImpact.length})`);
            });
        }
        
        return result;
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
