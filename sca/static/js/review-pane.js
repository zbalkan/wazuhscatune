/** Review list and reading pane interaction. */
class ReviewPane {
    constructor(checks, decisions = {}, stats = null) {
        this.checks = checks;
        this.decisions = decisions;
        this.currentCheckId = null;
        this.saveInFlight = false;
        this.dirty = false;

        this.list = document.getElementById('check-list');
        this.acceptRadio = document.querySelector('input[name="decision"][value="include"]');
        this.exceptionRadio = document.querySelector('input[name="decision"][value="exclude"]');
        this.justificationArea = document.getElementById('justification-area');
        this.justificationInput = document.getElementById('justification-input');
        this.justificationCount = document.getElementById('just-char-count');
        this.previousButton = document.getElementById('previous-btn');
        this.saveNextButton = document.getElementById('save-next-btn');

        this.bindEvents();
        this.updateAllRows();
        this.applyStats(stats || this.calculateStats());

        const firstUnreviewed = checks.find(check => !this.decisions[check.id]);
        const initial = firstUnreviewed || checks[0];
        if (initial) this.selectCheck(initial.id);
    }

    bindEvents() {
        this.list.querySelectorAll('.check-row').forEach(row => {
            row.addEventListener('click', () => this.selectCheck(row.dataset.checkId));
        });
        this.acceptRadio.addEventListener('change', () => {
            this.markDirty();
            this.updateDecisionForm();
        });
        this.exceptionRadio.addEventListener('change', () => {
            this.markDirty();
            this.updateDecisionForm();
        });
        this.justificationInput.addEventListener('input', () => {
            this.markDirty();
            this.justificationCount.textContent = this.justificationInput.value.length;
        });
        this.previousButton.addEventListener('click', () => this.selectPrevious());
        this.saveNextButton.addEventListener('click', () => this.saveAndNext());
    }

    markDirty() {
        this.dirty = true;
        document.getElementById('review-decisions-btn').disabled = true;
    }

    selectCheck(checkId) {
        const id = String(checkId);
        if (this.dirty && this.currentCheckId !== null && id !== this.currentCheckId) {
            showToast('Save this decision before moving to another check', 'error');
            return;
        }
        const check = this.checks.find(item => item.id === id);
        if (!check) return;

        this.currentCheckId = id;
        this.list.querySelectorAll('.check-row').forEach(row => {
            row.classList.toggle('selected', row.dataset.checkId === id);
            row.setAttribute('aria-current', row.dataset.checkId === id ? 'true' : 'false');
        });

        document.getElementById('detail-id').textContent = check.id;
        document.getElementById('detail-title').textContent = check.title;
        document.getElementById('detail-description').textContent = check.description || 'No description available';
        this.setOptionalDetail('impact', check.impact);
        this.setOptionalDetail('rationale', check.rationale);
        this.setOptionalDetail('remediation', check.remediation);
        this.renderCompliance(check.compliance || []);

        const decision = this.decisions[id];
        if (decision?.decision === 'exception') {
            this.exceptionRadio.checked = true;
            this.justificationInput.value = decision.justification || '';
        } else {
            this.acceptRadio.checked = true;
            this.justificationInput.value = '';
        }
        this.justificationCount.textContent = this.justificationInput.value.length;
        this.dirty = false;
        this.updateDecisionForm();
        this.updateNavigation();
    }

    clearSelection() {
        this.currentCheckId = null;
        this.dirty = false;
        this.list.querySelectorAll('.check-row').forEach(row => {
            row.classList.remove('selected');
            row.setAttribute('aria-current', 'false');
        });
        this.updateNavigation();
    }

    setOptionalDetail(field, value) {
        const group = document.getElementById(`${field}-group`);
        if (!value) {
            group.hidden = true;
            return;
        }
        document.getElementById(`detail-${field}`).textContent = value;
        group.hidden = false;
    }

    renderCompliance(compliance) {
        const group = document.getElementById('compliance-group');
        const container = document.getElementById('detail-compliance');
        container.replaceChildren();
        if (!compliance.length) {
            group.hidden = true;
            return;
        }
        const list = document.createElement('ul');
        compliance.forEach(item => {
            Object.entries(item).forEach(([key, values]) => {
                const row = document.createElement('li');
                const label = document.createElement('strong');
                label.textContent = `${key}: `;
                row.append(label, document.createTextNode(values.join(', ')));
                list.appendChild(row);
            });
        });
        container.appendChild(list);
        group.hidden = false;
    }

    updateDecisionForm() {
        this.justificationArea.hidden = !this.exceptionRadio.checked;
    }

    validateDecision() {
        if (!this.exceptionRadio.checked) return null;
        const length = this.justificationInput.value.trim().length;
        if (length < 10) return 'Justification must be at least 10 characters';
        if (length > 1000) return 'Justification must not exceed 1000 characters';
        return null;
    }

    async saveAndNext() {
        if (this.saveInFlight || this.currentCheckId === null) return;
        const error = this.validateDecision();
        if (error) {
            showToast(error, 'error');
            return;
        }

        const checkId = this.currentCheckId;
        const decision = this.exceptionRadio.checked ? 'exception' : 'accepted';
        const justification = this.justificationInput.value.trim();

        this.saveInFlight = true;
        this.previousButton.disabled = true;
        this.saveNextButton.disabled = true;
        try {
            const response = await fetch('/api/decision', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({check_id: checkId, decision, justification}),
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Failed to save decision');
            }

            this.decisions[checkId] = data.decision;
            this.updateRow(checkId, data.decision);
            this.dirty = false;
            this.applyStats(data.stats);
            document.dispatchEvent(new CustomEvent('reviewDecisionChanged', {
                detail: {checkId}
            }));
            showToast('Decision saved', 'success');

            const visibleIds = this.visibleIds();
            const nextId = this.nextVisibleId(checkId);
            if (nextId) {
                this.selectCheck(nextId);
            } else if (!visibleIds.includes(checkId)) {
                if (visibleIds.length) this.selectCheck(visibleIds[0]);
                else this.clearSelection();
            }
        } catch (error) {
            showToast(error.message || 'Error saving decision', 'error');
        } finally {
            this.saveInFlight = false;
            this.updateNavigation();
        }
    }

    updateRow(checkId, decision) {
        const row = this.rowFor(checkId);
        if (!row) return;
        const status = row.querySelector('.card-status');
        const isException = decision.decision === 'exception';
        status.textContent = isException ? 'Exception' : 'Accepted';
        status.dataset.status = isException ? 'exception' : 'accepted';
        row.classList.toggle('excluded', isException);
        row.classList.toggle('included', !isException);
    }

    updateAllRows() {
        Object.entries(this.decisions).forEach(([checkId, decision]) => {
            this.updateRow(checkId, decision);
        });
    }

    calculateStats() {
        const total = this.checks.length;
        const reviewed = Object.keys(this.decisions).length;
        const exceptions = Object.values(this.decisions).filter(item => item.decision === 'exception').length;
        return {
            total,
            reviewed,
            exceptions,
            unreviewed: total - reviewed,
            effective_included: total - exceptions,
            review_completion: total ? reviewed / total * 100 : 0,
        };
    }

    applyStats(stats) {
        document.getElementById('total-count').textContent = stats.total;
        document.getElementById('reviewed-count').textContent = stats.reviewed;
        document.getElementById('excluded-count').textContent = stats.exceptions;
        document.getElementById('unreviewed-count').textContent = stats.unreviewed;
        document.getElementById('effective-count').textContent = stats.effective_included;
        document.getElementById('progress-fill').style.width = `${stats.review_completion}%`;
        document.getElementById('review-decisions-btn').disabled = stats.unreviewed !== 0 || this.dirty;
    }

    filterRows(checkIds) {
        const visible = new Set(checkIds.map(String));
        this.list.querySelectorAll('.check-row').forEach(row => {
            row.hidden = !visible.has(row.dataset.checkId);
        });
    }

    rowFor(checkId) {
        return Array.from(this.list.querySelectorAll('.check-row'))
            .find(row => row.dataset.checkId === String(checkId));
    }

    visibleIds() {
        return Array.from(this.list.querySelectorAll('.check-row:not([hidden])'))
            .map(row => row.dataset.checkId);
    }

    nextVisibleId(checkId) {
        const ids = this.visibleIds();
        const index = ids.indexOf(String(checkId));
        return index >= 0 && index < ids.length - 1 ? ids[index + 1] : null;
    }

    previousVisibleId(checkId) {
        const ids = this.visibleIds();
        const index = ids.indexOf(String(checkId));
        return index > 0 ? ids[index - 1] : null;
    }

    selectPrevious() {
        const previous = this.previousVisibleId(this.currentCheckId);
        if (previous) this.selectCheck(previous);
    }

    updateNavigation() {
        this.previousButton.disabled = this.saveInFlight || !this.previousVisibleId(this.currentCheckId);
        this.saveNextButton.disabled = this.saveInFlight || this.currentCheckId === null;
    }
}

window.ReviewPane = ReviewPane;
