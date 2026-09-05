/**
 * Modal Handler
 * Manages modal interactions and check detail viewing
 */

const MIN_DISTINCT_LETTERS = 4;

function isMeaningfulJustification(text) {
    const letters = (text.toLowerCase().match(/[^\W\d_]/gu) || []);
    if (new Set(letters).size < MIN_DISTINCT_LETTERS) return false;
    const stripped = text.replace(/\s+/g, '');
    if (!stripped) return false;
    const counts = {};
    let mostCommonCount = 0;
    for (const char of stripped) {
        counts[char] = (counts[char] || 0) + 1;
        mostCommonCount = Math.max(mostCommonCount, counts[char]);
    }
    return mostCommonCount / stripped.length <= 0.5;
}

class ModalHandler {
    constructor(checks, decisions, cardManager) {
        this.checks = checks;
        this.decisions = decisions;
        this.cardManager = cardManager;
        this.currentCheckId = null;
        this.previouslyFocusedElement = null;
        this.saveInFlight = false;

        this.modal = document.getElementById('check-modal');
        this.modalTitle = document.getElementById('modal-title');
        this.modalBody = document.getElementById('modal-body');
        this.closeBtn = document.getElementById('modal-close-btn');
        this.prevBtn = document.getElementById('modal-prev-btn');
        this.nextBtn = document.getElementById('modal-next-btn');
        this.saveBtn = document.getElementById('modal-save-btn');
        this.includeRadio = document.querySelector('input[name="decision"][value="include"]');
        this.excludeRadio = document.querySelector('input[name="decision"][value="exclude"]');
        this.justificationArea = document.getElementById('justification-area');
        this.justificationInput = document.getElementById('justification-input');
        this.justCharCount = document.getElementById('just-char-count');

        this.initializeEventListeners();
    }

    initializeEventListeners() {
        this.closeBtn.addEventListener('click', () => this.closeModal());
        this.modal.querySelector('.modal-overlay').addEventListener('click', () => this.closeModal());
        this.prevBtn.addEventListener('click', () => this.navigatePrevious());
        this.nextBtn.addEventListener('click', () => this.navigateNext());
        this.saveBtn.addEventListener('click', () => this.saveDecision());

        document.querySelectorAll('input[name="decision"]').forEach(radio => {
            radio.addEventListener('change', () => this.handleDecisionChange());
        });
        this.justificationInput.addEventListener('input', () => {
            this.justCharCount.textContent = this.justificationInput.value.length;
        });
        document.addEventListener('openCheckModal', (e) => this.openModal(e.detail.checkId));

        document.addEventListener('keydown', (e) => {
            if (this.modal.style.display === 'none') return;
            if (e.key === 'Tab') {
                this.trapFocus(e);
                return;
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                this.closeModal();
                return;
            }

            const target = e.target;
            const editing = target instanceof HTMLInputElement ||
                target instanceof HTMLTextAreaElement ||
                target instanceof HTMLSelectElement ||
                (target instanceof HTMLElement && target.isContentEditable);

            if (e.key === 'ArrowLeft' && !editing) {
                e.preventDefault();
                this.navigatePrevious();
            } else if (e.key === 'ArrowRight' && !editing) {
                e.preventDefault();
                this.navigateNext();
            } else if (e.key === 'Enter' && e.ctrlKey && !e.repeat) {
                e.preventDefault();
                this.saveDecision();
            }
        });
    }

    getFocusableElements() {
        return Array.from(this.modal.querySelectorAll(
            'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), ' +
            'select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
        )).filter(element => element.offsetParent !== null);
    }

    trapFocus(event) {
        const focusableElements = this.getFocusableElements();
        if (focusableElements.length === 0) {
            event.preventDefault();
            return;
        }
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        const activeElement = document.activeElement;

        if (!focusableElements.includes(activeElement)) {
            event.preventDefault();
            firstElement.focus();
        } else if (event.shiftKey && activeElement === firstElement) {
            event.preventDefault();
            lastElement.focus();
        } else if (!event.shiftKey && activeElement === lastElement) {
            event.preventDefault();
            firstElement.focus();
        }
    }

    openModal(checkId) {
        this.previouslyFocusedElement = document.activeElement;
        this.currentCheckId = String(checkId);
        this.loadCheckData(this.currentCheckId);
        this.modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
        this.closeBtn.focus();
    }

    closeModal() {
        this.modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        this.currentCheckId = null;
        if (this.previouslyFocusedElement instanceof HTMLElement &&
            document.contains(this.previouslyFocusedElement)) {
            this.previouslyFocusedElement.focus();
        }
        this.previouslyFocusedElement = null;
    }

    loadCheckData(checkId) {
        try {
            const normalizedId = String(checkId);
            const check = this.checks.find(c => c.id === normalizedId);
            if (!check) {
                showToast('Check not found', 'error');
                return;
            }
            const decision = this.decisions[normalizedId] || { decision: 'unreviewed' };
            document.getElementById('detail-id').textContent = check.id;
            document.getElementById('detail-title').textContent = check.title;
            document.getElementById('detail-description').textContent = check.description || 'No description available';

            const optional = [
                ['impact', 'detail-impact'], ['rationale', 'detail-rationale'],
                ['remediation', 'detail-remediation']
            ];
            optional.forEach(([field, detailId]) => {
                const group = document.getElementById(`${field}-group`);
                if (check[field]) {
                    document.getElementById(detailId).textContent = check[field];
                    group.style.display = 'flex';
                } else {
                    group.style.display = 'none';
                }
            });

            const complianceGroup = document.getElementById('compliance-group');
            const complianceEl = document.getElementById('detail-compliance');
            if (check.compliance && check.compliance.length > 0) {
                complianceEl.replaceChildren(this.formatCompliance(check.compliance));
                complianceGroup.style.display = 'flex';
            } else {
                complianceGroup.style.display = 'none';
            }

            if (decision.decision === 'exception') {
                this.excludeRadio.checked = true;
                this.justificationArea.style.display = 'block';
                this.justificationInput.value = decision.justification || '';
                this.justCharCount.textContent = this.justificationInput.value.length;
            } else {
                this.includeRadio.checked = true;
                this.justificationArea.style.display = 'none';
                this.justificationInput.value = '';
                this.justCharCount.textContent = '0';
            }
            this.updateNavigationButtons();
        } catch (error) {
            showToast('Error loading check details', 'error');
            console.error(error);
        }
    }

    formatCompliance(complianceList) {
        const container = document.createElement('ul');
        container.style.margin = '0';
        container.style.paddingLeft = '1.5rem';
        complianceList.forEach(comp => {
            Object.entries(comp).forEach(([key, values]) => {
                if (values && values.length > 0) {
                    const li = document.createElement('li');
                    const strong = document.createElement('strong');
                    strong.textContent = key.replace(/_/g, ' ').toUpperCase() + ': ';
                    li.appendChild(strong);
                    li.appendChild(document.createTextNode(values.join(', ')));
                    container.appendChild(li);
                }
            });
        });
        return container;
    }

    handleDecisionChange() {
        if (this.excludeRadio.checked) {
            this.justificationArea.style.display = 'block';
            this.justificationInput.focus();
        } else {
            this.justificationArea.style.display = 'none';
        }
    }

    validateJustification() {
        const justification = this.justificationInput.value.trim();
        if (this.excludeRadio.checked) {
            if (!justification || justification.length < 10) return 'Justification must be at least 10 characters';
            if (justification.length > 1000) return 'Justification must not exceed 1000 characters';
            if (!isMeaningfulJustification(justification)) {
                return 'Justification must contain meaningful text, not repeated characters';
            }
        }
        return null;
    }

    async saveDecision() {
        if (this.saveInFlight) return;
        const validationError = this.validateJustification();
        if (validationError) {
            showToast(validationError, 'error');
            return;
        }

        const decision = this.excludeRadio.checked ? 'exception' : 'accepted';
        const justification = this.justificationInput.value.trim();
        this.saveInFlight = true;
        this.saveBtn.disabled = true;

        try {
            const response = await fetch('/api/decision', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    check_id: this.currentCheckId,
                    decision: decision,
                    justification: justification
                })
            });
            const data = await response.json();
            if (data.success) {
                const normalized = data.decision;
                this.decisions[this.currentCheckId] = normalized;
                this.cardManager.updateCard(this.currentCheckId, normalized);
                this.cardManager.applyStats(data.stats);
                showToast('Decision saved', 'success');
            } else {
                showToast(data.error || 'Failed to save decision', 'error');
            }
        } catch (error) {
            showToast('Error saving decision', 'error');
            console.error(error);
        } finally {
            this.saveInFlight = false;
            this.saveBtn.disabled = false;
        }
    }

    navigatePrevious() {
        const currentIndex = this.checks.findIndex(c => c.id === this.currentCheckId);
        if (currentIndex > 0) {
            this.currentCheckId = this.checks[currentIndex - 1].id;
            this.loadCheckData(this.currentCheckId);
        }
    }

    navigateNext() {
        const currentIndex = this.checks.findIndex(c => c.id === this.currentCheckId);
        if (currentIndex < this.checks.length - 1) {
            this.currentCheckId = this.checks[currentIndex + 1].id;
            this.loadCheckData(this.currentCheckId);
        }
    }

    updateNavigationButtons() {
        const currentIndex = this.checks.findIndex(c => c.id === this.currentCheckId);
        this.prevBtn.disabled = currentIndex <= 0;
        this.nextBtn.disabled = currentIndex >= this.checks.length - 1;
    }
}

window.ModalHandler = ModalHandler;
