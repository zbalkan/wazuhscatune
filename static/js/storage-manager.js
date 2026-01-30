/**
 * Storage Manager
 * Handles auto-save and LocalStorage management
 */

class StorageManager {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.autoSaveInterval = null;
        this.isSaved = true;
        
        // Start auto-save
        this.startAutoSave();
    }
    
    startAutoSave() {
        // Auto-save every 30 seconds
        this.autoSaveInterval = setInterval(() => {
            this.autoSave();
        }, 30000);
    }
    
    stopAutoSave() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
            this.autoSaveInterval = null;
        }
    }
    
    async autoSave() {
        try {
            const response = await fetch('/api/save-draft', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.markAsSaved();
                console.log('Auto-save successful');
            } else {
                console.error('Auto-save failed:', data.error);
            }
        } catch (error) {
            console.error('Auto-save error:', error);
        }
    }
    
    saveToLocalStorage(data) {
        try {
            const key = `sca_draft_${this.sessionId}`;
            localStorage.setItem(key, JSON.stringify(data));
            console.log('Saved to localStorage');
        } catch (error) {
            console.error('LocalStorage save error:', error);
        }
    }
    
    loadFromLocalStorage() {
        try {
            const key = `sca_draft_${this.sessionId}`;
            const data = localStorage.getItem(key);
            if (data) {
                return JSON.parse(data);
            }
            return null;
        } catch (error) {
            console.error('LocalStorage load error:', error);
            return null;
        }
    }
    
    clearLocalStorage() {
        try {
            const key = `sca_draft_${this.sessionId}`;
            localStorage.removeItem(key);
            console.log('Cleared localStorage');
        } catch (error) {
            console.error('LocalStorage clear error:', error);
        }
    }
    
    async syncWithBackend() {
        // Sync local storage with backend
        const localData = this.loadFromLocalStorage();
        if (localData) {
            // Could implement sync logic here if needed
            console.log('Local data available:', localData);
        }
    }
    
    markAsSaved() {
        this.isSaved = true;
        if (window.markAsSaved) {
            window.markAsSaved();
        }
    }
    
    markAsUnsaved() {
        this.isSaved = false;
        if (window.markAsUnsaved) {
            window.markAsUnsaved();
        }
    }
}

// Make globally available
window.StorageManager = StorageManager;
