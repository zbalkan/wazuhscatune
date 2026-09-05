/**
 * Main Application Logic
 * Global utilities and toast notification system
 */

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
    toast.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');

    const messageEl = document.createElement('p');
    messageEl.className = 'toast-message';
    messageEl.textContent = message;

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'toast-close';
    closeBtn.setAttribute('aria-label', 'Dismiss notification');
    closeBtn.innerHTML = '&times;';
    closeBtn.onclick = () => removeToast(toast);

    toast.appendChild(messageEl);
    toast.appendChild(closeBtn);
    container.appendChild(toast);
    setTimeout(() => removeToast(toast), 3000);
}

function removeToast(toast) {
    toast.style.animation = 'slideIn 0.3s ease reverse';
    setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
}

async function fetchJSON(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {'Content-Type': 'application/json', ...options.headers}
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Request failed');
        return data;
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const modal = document.getElementById('check-modal');
        if (modal && modal.style.display !== 'none') {
            const closeBtn = document.getElementById('modal-close-btn');
            if (closeBtn) closeBtn.click();
        }
    }
});

let hasUnsavedChanges = false;
function markAsUnsaved() { hasUnsavedChanges = true; }
function markAsSaved() { hasUnsavedChanges = false; }

window.addEventListener('beforeunload', function(e) {
    if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
        return '';
    }
});

window.showToast = showToast;
window.fetchJSON = fetchJSON;
window.markAsUnsaved = markAsUnsaved;
window.markAsSaved = markAsSaved;
