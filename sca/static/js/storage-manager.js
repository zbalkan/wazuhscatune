/** Periodically asks the authoritative server session to persist its draft. */
class StorageManager {
    constructor() {
        this.autoSaveInterval = setInterval(() => this.autoSave(), 30000);
    }

    async autoSave() {
        try {
            const response = await fetch('/api/save-draft', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            if (!response.ok) {
                showToast('Automatic draft save failed', 'error');
            }
        } catch (_) {
            showToast('Automatic draft save failed', 'error');
        }
    }

    stop() {
        clearInterval(this.autoSaveInterval);
    }
}

window.StorageManager = StorageManager;
