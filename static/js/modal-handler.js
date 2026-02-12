/**
 * Modal Handler
 * Manages modal interactions and check detail viewing
 */

class ModalHandler {
    constructor(checks, decisions, cardManager) {
        this.checks = checks;
        this.decisions = decisions;
        this.cardManager = cardManager;
        this.currentCheckId = null;
        
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
        // Close modal
        this.closeBtn.addEventListener('click', () => this.closeModal());
        this.modal.querySelector('.modal-overlay').addEventListener('click', () => this.closeModal());
        
        // Navigation
        this.prevBtn.addEventListener('click', () => this.navigatePrevious());
        this.nextBtn.addEventListener('click', () => this.navigateNext());
        
        // Save
        this.saveBtn.addEventListener('click', () => this.saveDecision());
        
        // Radio button change
        const radios = document.querySelectorAll('input[name="decision"]');
        radios.forEach(radio => {
            radio.addEventListener('change', () => this.handleDecisionChange());
        });
        
        // Justification character count
        this.justificationInput.addEventListener('input', () => {
            this.justCharCount.textContent = this.justificationInput.value.length;
        });
        
        // Listen for openCheckModal event
        document.addEventListener('openCheckModal', (e) => {
            this.openModal(e.detail.checkId);
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (this.modal.style.display !== 'none') {
                if (e.key === 'ArrowLeft') {
                    e.preventDefault();
                    this.navigatePrevious();
                } else if (e.key === 'ArrowRight') {
                    e.preventDefault();
                    this.navigateNext();
                } else if (e.key === 'Enter' && e.ctrlKey) {
                    e.preventDefault();
                    this.saveDecision();
                }
            }
        });
    }
    
    openModal(checkId) {
        this.currentCheckId = checkId;
        this.loadCheckData(checkId);
        this.modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
    
    closeModal() {
        this.modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        this.currentCheckId = null;
    }
    
    async loadCheckData(checkId) {
        try {
            const response = await fetch(`/api/check/${checkId}`);
            const check = await response.json();
            
            if (check.error) {
                showToast(check.error, 'error');
                return;
            }
            
            // Populate modal
            document.getElementById('detail-id').textContent = check.id;
            document.getElementById('detail-title').textContent = check.title;
            document.getElementById('detail-description').textContent = check.description || 'No description available';
            
            // Impact
            const impactGroup = document.getElementById('impact-group');
            if (check.impact) {
                document.getElementById('detail-impact').textContent = check.impact;
                impactGroup.style.display = 'flex';
            } else {
                impactGroup.style.display = 'none';
            }
            
            // Rationale
            const rationaleGroup = document.getElementById('rationale-group');
            if (check.rationale) {
                document.getElementById('detail-rationale').textContent = check.rationale;
                rationaleGroup.style.display = 'flex';
            } else {
                rationaleGroup.style.display = 'none';
            }
            
            // Remediation
            const remediationGroup = document.getElementById('remediation-group');
            if (check.remediation) {
                document.getElementById('detail-remediation').textContent = check.remediation;
                remediationGroup.style.display = 'flex';
            } else {
                remediationGroup.style.display = 'none';
            }
            
            // Compliance
            const complianceGroup = document.getElementById('compliance-group');
            const complianceEl = document.getElementById('detail-compliance');
            if (check.compliance && check.compliance.length > 0) {
                const container = this.formatCompliance(check.compliance);
                complianceEl.replaceChildren(container);
                complianceGroup.style.display = 'flex';
            } else {
                complianceGroup.style.display = 'none';
            }
            
            // Set decision state
            if (check.excluded) {
                this.excludeRadio.checked = true;
                this.justificationArea.style.display = 'block';
                this.justificationInput.value = check.justification || '';
                this.justCharCount.textContent = this.justificationInput.value.length;
            } else {
                this.includeRadio.checked = true;
                this.justificationArea.style.display = 'none';
                this.justificationInput.value = '';
                this.justCharCount.textContent = '0';
            }
            
            // Update navigation buttons
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
                    const formattedKey = key.replace(/_/g, ' ').toUpperCase();
                    strong.textContent = formattedKey + ': ';
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
        const excluded = this.excludeRadio.checked;
        const justification = this.justificationInput.value.trim();
        
        if (excluded) {
            if (!justification || justification.length < 10) {
                return 'Justification must be at least 10 characters';
            }
            if (justification.length > 1000) {
                return 'Justification must not exceed 1000 characters';
            }
        }
        
        return null;
    }
    
    async saveDecision() {
        const validationError = this.validateJustification();
        if (validationError) {
            showToast(validationError, 'error');
            return;
        }
        
        const excluded = this.excludeRadio.checked;
        const justification = this.justificationInput.value.trim();
        
        try {
            const response = await fetch('/api/decision', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    check_id: this.currentCheckId,
                    excluded: excluded,
                    justification: justification
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update card manager
                this.cardManager.updateCard(this.currentCheckId, { excluded, justification });
                showToast('Decision saved', 'success');
                this.closeModal();
            } else {
                showToast(data.error || 'Failed to save decision', 'error');
            }
        } catch (error) {
            showToast('Error saving decision', 'error');
            console.error(error);
        }
    }
    
    navigatePrevious() {
        const currentIndex = this.checks.findIndex(c => c.id === this.currentCheckId);
        if (currentIndex > 0) {
            const prevCheck = this.checks[currentIndex - 1];
            this.loadCheckData(prevCheck.id);
            this.currentCheckId = prevCheck.id;
        }
    }
    
    navigateNext() {
        const currentIndex = this.checks.findIndex(c => c.id === this.currentCheckId);
        if (currentIndex < this.checks.length - 1) {
            const nextCheck = this.checks[currentIndex + 1];
            this.loadCheckData(nextCheck.id);
            this.currentCheckId = nextCheck.id;
        }
    }
    
    updateNavigationButtons() {
        const currentIndex = this.checks.findIndex(c => c.id === this.currentCheckId);
        this.prevBtn.disabled = currentIndex <= 0;
        this.nextBtn.disabled = currentIndex >= this.checks.length - 1;
    }
}

// Make globally available
window.ModalHandler = ModalHandler;
