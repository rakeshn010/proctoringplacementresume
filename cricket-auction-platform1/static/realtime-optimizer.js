/**
 * Real-time Update Optimizer
 * Improves WebSocket performance and adds optimistic UI updates
 * Version: 1.0.0
 */

class RealtimeOptimizer {
    constructor() {
        this.pendingUpdates = new Map();
        this.updateQueue = [];
        this.isProcessing = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.connectionQuality = 'good'; // good, fair, poor
        this.latencyHistory = [];
        this.maxLatencyHistory = 10;
    }

    // Optimistic UI update - update immediately, rollback if server rejects
    optimisticUpdate(key, updateFn, rollbackFn) {
        const updateId = Date.now() + Math.random();
        
        // Apply update immediately
        updateFn();
        
        // Store rollback function
        this.pendingUpdates.set(updateId, {
            key,
            rollback: rollbackFn,
            timestamp: Date.now()
        });
        
        return updateId;
    }

    // Confirm optimistic update succeeded
    confirmUpdate(updateId) {
        this.pendingUpdates.delete(updateId);
    }

    // Rollback failed optimistic update
    rollbackUpdate(updateId) {
        const update = this.pendingUpdates.get(updateId);
        if (update && update.rollback) {
            update.rollback();
            this.pendingUpdates.delete(updateId);
        }
    }

    // Batch multiple updates together
    batchUpdate(updates) {
        this.updateQueue.push(...updates);
        
        if (!this.isProcessing) {
            this.processQueue();
        }
    }

    async processQueue() {
        if (this.updateQueue.length === 0) {
            this.isProcessing = false;
            return;
        }

        this.isProcessing = true;
        const batch = this.updateQueue.splice(0, 10); // Process 10 at a time

        // Apply all updates in batch
        batch.forEach(update => {
            if (typeof update === 'function') {
                update();
            }
        });

        // Schedule next batch
        requestAnimationFrame(() => this.processQueue());
    }

    // Measure connection latency
    measureLatency(startTime) {
        const latency = Date.now() - startTime;
        this.latencyHistory.push(latency);
        
        if (this.latencyHistory.length > this.maxLatencyHistory) {
            this.latencyHistory.shift();
        }

        // Calculate average latency
        const avgLatency = this.latencyHistory.reduce((a, b) => a + b, 0) / this.latencyHistory.length;

        // Update connection quality
        if (avgLatency < 100) {
            this.connectionQuality = 'good';
        } else if (avgLatency < 300) {
            this.connectionQuality = 'fair';
        } else {
            this.connectionQuality = 'poor';
        }

        return {
            current: latency,
            average: avgLatency,
            quality: this.connectionQuality
        };
    }

    // Get connection quality indicator
    getQualityIndicator() {
        const indicators = {
            good: { color: '#00ff88', text: 'Excellent', icon: '●' },
            fair: { color: '#ffd700', text: 'Good', icon: '●' },
            poor: { color: '#ff4757', text: 'Slow', icon: '●' }
        };
        return indicators[this.connectionQuality];
    }

    // Exponential backoff for reconnection
    getReconnectDelay() {
        const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts), 30000);
        this.reconnectAttempts++;
        return delay;
    }

    resetReconnect() {
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
    }

    // Debounce function for rapid updates
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Throttle function for limiting update frequency
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // Prefetch data before it's needed
    async prefetch(url, cacheKey) {
        try {
            const response = await fetch(url);
            const data = await response.json();
            sessionStorage.setItem(cacheKey, JSON.stringify({
                data,
                timestamp: Date.now()
            }));
            return data;
        } catch (error) {
            console.error('Prefetch error:', error);
            return null;
        }
    }

    // Get cached data if fresh enough
    getCached(cacheKey, maxAge = 5000) {
        const cached = sessionStorage.getItem(cacheKey);
        if (!cached) return null;

        const { data, timestamp } = JSON.parse(cached);
        if (Date.now() - timestamp > maxAge) {
            sessionStorage.removeItem(cacheKey);
            return null;
        }

        return data;
    }
}

// Global instance
window.realtimeOptimizer = new RealtimeOptimizer();

// Add connection quality indicator to page
function addConnectionIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'connection-indicator';
    indicator.style.cssText = `
        position: fixed;
        top: 10px;
        right: 10px;
        padding: 8px 12px;
        background: rgba(0, 0, 0, 0.8);
        border-radius: 20px;
        font-size: 12px;
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 6px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
    `;
    document.body.appendChild(indicator);

    // Update indicator every 2 seconds
    setInterval(() => {
        const quality = window.realtimeOptimizer.getQualityIndicator();
        indicator.innerHTML = `
            <span style="color: ${quality.color}; font-size: 16px;">${quality.icon}</span>
            <span style="color: #fff;">${quality.text}</span>
        `;
    }, 2000);
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addConnectionIndicator);
} else {
    addConnectionIndicator();
}
