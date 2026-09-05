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

        this.initializeCards();
        this.updateAllCards();
        stats ? this.applyStats(stats) : this.updateProgress();
    }

    initializeCards() {
        const cards = this.grid.querySelectorAll('.check-card');
        cards.forEach(card => {
            const openCard = () => {
                const checkId = card.dataset.checkId;
                const event = new CustomEvent('openCheckModal', { detail: { checkId } });
                document.dispatchEvent(event);
            };

            card.addEventListener('click', openCard);
            card.addEventListener('keydown', (event) => {
                if ((event.key === 'Enter' || event.key === ' ') && !event.repeat) {
                    event.preventDefault();
                    openCard();
                }
            });
        });
    }

    updateCard(checkId, decision) {
        const card = this.getCardElement(checkId);
        if (!card) return;

        this.decisions[checkId] = decision;
        card.classList.remove('included', 'excluded', 'modified');

        if (decision.decision === 'exception') {
            card.classList.add('excluded');
        } else {
            card.classList.add('included');
        }

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

        document.dispatchEvent(new CustomEvent('cardDecisionChanged', {
            detail: { checkId: String(checkId) }
        }));
    }

    updateAllCards() {
        Object.keys(this.decisions).forEach(checkId => {
            this.updateCard(checkId, this.decisions[checkId]);
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
        return Array.from(this.grid.querySelectorAll('.check-card'))
            .find(card => card.dataset.checkId === String(checkId));
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
        const visibleIds = new Set(filteredCheckIds.map(String));
        const cards = this.grid.querySelectorAll('.check-card');

        cards.forEach(card => {
            card.style.display = visibleIds.has(card.dataset.checkId) ? 'block' : 'none';
        });
    }
}

window.CardManager = CardManager;
