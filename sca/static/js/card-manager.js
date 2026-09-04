/**
 * Card Manager
 * Manages the card grid display and updates
 */

class CardManager {
    constructor(checks, decisions = {}, stats = null) {
        
        this.checks = checks;
        this.decisions = decisions;
        this.grid = document.getElementById('cards-grid');
        
        if (!this.grid) {
            console.error('[CardManager] ERROR: cards-grid element not found!');
            return;
        }
        
        // Initialize card click handlers
        this.initializeCards();
        this.updateAllCards();
        stats ? this.applyStats(stats) : this.updateProgress();
    }
    
    initializeCards() {
        const cards = this.grid.querySelectorAll('.check-card');
        cards.forEach(card => {
            card.addEventListener('click', () => {
                const checkId = parseInt(card.dataset.checkId);
                // Trigger modal open (will be handled by ModalHandler)
                const event = new CustomEvent('openCheckModal', { detail: { checkId } });
                document.dispatchEvent(event);
            });
        });
    }
    
    updateCard(checkId, decision) {
        const card = this.getCardElement(checkId);
        if (!card) return;
        
        // Update decisions
        this.decisions[checkId] = decision;
        
        // Update card styling
        card.classList.remove('included', 'excluded', 'modified');
        
        if (decision.decision === 'exception') {
            card.classList.add('excluded');
        } else {
            card.classList.add('included');
        }
        
        // Update status badge
        const statusEl = card.querySelector('.card-status');
        if (statusEl) {
            if (decision.decision === 'exception') {
                statusEl.textContent = 'Exception';
                statusEl.dataset.status = 'exception';
            } else {
                statusEl.textContent = 'Accepted';
                statusEl.dataset.status = 'accepted';
            }
        }
        
    }
    
    updateAllCards() {
        Object.keys(this.decisions).forEach(checkId => {
            const decision = this.decisions[checkId];
            this.updateCard(parseInt(checkId), decision);
        });
    }
    
    highlightCard(checkId) {
        const card = this.getCardElement(checkId);
        if (card) {
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
            card.style.outline = '2px solid var(--color-primary)';
            setTimeout(() => {
                card.style.outline = '';
            }, 2000);
        }
    }
    
    getCardElement(checkId) {
        return this.grid.querySelector(`[data-check-id="${checkId}"]`);
    }
    
    updateProgress() {
        const totalEl = document.getElementById('total-count');
        const reviewedEl = document.getElementById('reviewed-count');
        const excludedEl = document.getElementById('excluded-count');
        const progressFill = document.getElementById('progress-fill');
        
        const total = this.checks.length;
        const reviewed = Object.keys(this.decisions).length;
        const excluded = Object.values(this.decisions).filter(d => d.decision === 'exception').length;
        
        if (totalEl) totalEl.textContent = total;
        if (reviewedEl) reviewedEl.textContent = reviewed;
        if (excludedEl) excludedEl.textContent = excluded;
        
        if (progressFill) {
            const percentage = total > 0 ? (reviewed / total) * 100 : 0;
            progressFill.style.width = percentage + '%';
        }
    }

    applyStats(stats) {
        if (!stats) return;
        document.getElementById('total-count').textContent = stats.total;
        document.getElementById('reviewed-count').textContent = stats.reviewed;
        document.getElementById('excluded-count').textContent = stats.exceptions;
        const unreviewed = document.getElementById('unreviewed-count');
        const effective = document.getElementById('effective-count');
        if (unreviewed) unreviewed.textContent = stats.unreviewed;
        if (effective) effective.textContent = stats.effective_included;
        document.getElementById('progress-fill').style.width = stats.review_completion + '%';
    }
    
    filterCards(filteredCheckIds) {
        const cards = this.grid.querySelectorAll('.check-card');
        
        cards.forEach(card => {
            const checkId = parseInt(card.dataset.checkId);
            if (filteredCheckIds.includes(checkId)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }
}

// Make globally available
window.CardManager = CardManager;
