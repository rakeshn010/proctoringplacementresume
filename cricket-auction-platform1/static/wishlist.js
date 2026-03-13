/**
 * Player Wishlist System
 * Version: 1.0.0
 */

let myWishlist = [];

// Initialize wishlist
async function initWishlist() {
    await loadMyWishlist();
}

// Load user's wishlist
async function loadMyWishlist() {
    try {
        const res = await api('/wishlist/my-wishlist');
        const data = await res.json();
        
        if (data.ok) {
            myWishlist = data.wishlist;
            renderWishlist();
            updateWishlistBadge();
        }
    } catch (error) {
        console.error('Error loading wishlist:', error);
    }
}

// Render wishlist
function renderWishlist() {
    const container = document.getElementById('wishlist-container');
    if (!container) return;
    
    if (myWishlist.length === 0) {
        container.innerHTML = `
            <div class="wishlist-empty">
                <i class="bi bi-star" style="font-size: 48px; color: #ffd700;"></i>
                <h4>Your Wishlist is Empty</h4>
                <p>Add players to your wishlist to get notified when they go live!</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = myWishlist.map(item => {
        const player = item.player_details;
        if (!player) return '';
        
        const priorityClass = item.priority === 1 ? 'high' : item.priority === 2 ? 'medium' : 'low';
        const priorityText = item.priority === 1 ? 'High' : item.priority === 2 ? 'Medium' : 'Low';
        
        const defaultImg = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="280" height="220"%3E%3Crect fill="%230a0a0a" width="280" height="220"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="80" fill="%23ffd700"%3E👤%3C/text%3E%3C/svg%3E';
        const imageSrc = player.image_path || defaultImg;
        
        return `
            <div class="wishlist-item ${player.is_live ? 'live' : ''}">
                ${player.is_live ? '<div class="wishlist-live-badge">🔴 LIVE NOW</div>' : ''}
                <img src="${imageSrc}" class="wishlist-player-img" alt="${player.name}" onerror="this.src='${defaultImg}'">
                <div class="wishlist-item-body">
                    <div class="wishlist-player-name">${player.name}</div>
                    <div class="wishlist-player-meta">
                        <span class="badge bg-primary">${player.role}</span>
                        ${player.category ? `<span class="badge bg-secondary">${player.category}</span>` : ''}
                        <span class="badge bg-${priorityClass}">${priorityText} Priority</span>
                    </div>
                    <div class="wishlist-player-price">Base: ₹${(player.base_price || 0).toLocaleString()}</div>
                    ${item.max_bid ? `<div class="wishlist-max-bid">Max Bid: ₹${item.max_bid.toLocaleString()}</div>` : ''}
                    <div class="wishlist-item-actions">
                        <button class="btn btn-sm btn-primary" onclick="updateWishlistPriority('${item.player_id}')">
                            <i class="bi bi-pencil"></i> Edit
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="removeFromWishlist('${item.player_id}')">
                            <i class="bi bi-trash"></i> Remove
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Add player to wishlist
async function addToWishlist(playerId, playerName) {
    try {
        // Show priority selection modal
        const priority = await showPriorityModal(playerName);
        if (!priority) return;
        
        const res = await api(`/wishlist/add/${playerId}?priority=${priority}`, {
            method: 'POST'
        });
        
        const data = await res.json();
        
        if (data.ok) {
            showToast('Added to Wishlist', `${playerName} added to your wishlist`, 'success');
            await loadMyWishlist();
        } else {
            alert(data.detail || 'Failed to add to wishlist');
        }
    } catch (error) {
        console.error('Error adding to wishlist:', error);
        alert('Error adding to wishlist');
    }
}

// Remove from wishlist
async function removeFromWishlist(playerId) {
    if (!confirm('Remove this player from your wishlist?')) return;
    
    try {
        const res = await api(`/wishlist/remove/${playerId}`, {
            method: 'DELETE'
        });
        
        const data = await res.json();
        
        if (data.ok) {
            showToast('Removed', 'Player removed from wishlist', 'success');
            await loadMyWishlist();
        } else {
            alert('Failed to remove from wishlist');
        }
    } catch (error) {
        console.error('Error removing from wishlist:', error);
        alert('Error removing from wishlist');
    }
}

// Check if player is in wishlist
async function isInWishlist(playerId) {
    try {
        const res = await api(`/wishlist/check/${playerId}`);
        const data = await res.json();
        return data.in_wishlist;
    } catch (error) {
        console.error('Error checking wishlist:', error);
        return false;
    }
}

// Show priority selection modal
function showPriorityModal(playerName) {
    return new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'wishlist-priority-modal';
        modal.innerHTML = `
            <div class="wishlist-priority-content">
                <h3>Add to Wishlist</h3>
                <p>Select priority for <strong>${playerName}</strong></p>
                <div class="priority-options">
                    <button class="priority-btn high" onclick="selectPriority(1)">
                        <i class="bi bi-star-fill"></i> High Priority
                    </button>
                    <button class="priority-btn medium" onclick="selectPriority(2)">
                        <i class="bi bi-star-half"></i> Medium Priority
                    </button>
                    <button class="priority-btn low" onclick="selectPriority(3)">
                        <i class="bi bi-star"></i> Low Priority
                    </button>
                </div>
                <button class="btn btn-secondary mt-3" onclick="closePriorityModal()">Cancel</button>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        window.selectPriority = (priority) => {
            modal.remove();
            resolve(priority);
        };
        
        window.closePriorityModal = () => {
            modal.remove();
            resolve(null);
        };
    });
}

// Update wishlist badge count
function updateWishlistBadge() {
    const badge = document.getElementById('wishlist-badge');
    if (badge) {
        badge.textContent = myWishlist.length;
        badge.style.display = myWishlist.length > 0 ? 'inline-block' : 'none';
    }
}

// Toggle wishlist panel
function toggleWishlistPanel() {
    const panel = document.getElementById('wishlist-panel');
    if (panel) {
        panel.classList.toggle('open');
    }
}

// Handle wishlist player going live (via WebSocket)
function handleWishlistPlayerLive(playerId) {
    const item = myWishlist.find(w => w.player_id === playerId);
    if (item && notificationPreferences.playerLive) {
        showTeamNotification('⭐ Wishlist Player Live!', {
            body: `${item.player_name} is now live for bidding`,
            tag: 'wishlist-live',
            vibrate: [300, 100, 300, 100, 300]
        });
    }
}

// Expose functions globally
window.initWishlist = initWishlist;
window.addToWishlist = addToWishlist;
window.removeFromWishlist = removeFromWishlist;
window.isInWishlist = isInWishlist;
window.toggleWishlistPanel = toggleWishlistPanel;
window.handleWishlistPlayerLive = handleWishlistPlayerLive;
