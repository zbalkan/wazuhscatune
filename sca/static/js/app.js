/**
 * Main Application Logic
 * Global utilities and toast notification system
 */

// Toast notification system
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const messageEl = document.createElement('p');
    messageEl.className = 'toast-message';
    messageEl.textContent = message;
    
    const closeBtn = document.createElement('button');
    closeBtn.className = 'toast-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.onclick = () => removeToast(toast);
    
    toast.appendChild(messageEl);
    toast.appendChild(closeBtn);
    container.appendChild(toast);
    
    // Auto-dismiss after 3 seconds
    setTimeout(() => removeToast(toast), 3000);
}

function removeToast(toast) {
    toast.style.animation = 'slideIn 0.3s ease reverse';
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 300);
}

// AJAX helper function
async function fetchJSON(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }
        
        return data;
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

// Keyboard shortcut handlers
document.addEventListener('keydown', function(e) {
    // ESC key to close modal
    if (e.key === 'Escape') {
        const modal = document.getElementById('check-modal');
        if (modal && modal.style.display !== 'none') {
            const closeBtn = document.getElementById('modal-close-btn');
            if (closeBtn) closeBtn.click();
        }
    }
});

// Warn user before leaving page with unsaved changes
let hasUnsavedChanges = false;

function markAsUnsaved() {
    hasUnsavedChanges = true;
}

function markAsSaved() {
    hasUnsavedChanges = false;
}

window.addEventListener('beforeunload', function(e) {
    if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
        return '';
    }
});

// Make functions globally available
window.showToast = showToast;
window.fetchJSON = fetchJSON;
window.markAsUnsaved = markAsUnsaved;
window.markAsSaved = markAsSaved;
