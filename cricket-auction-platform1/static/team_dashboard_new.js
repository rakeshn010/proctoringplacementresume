/**
 * Advanced Team Dashboard JavaScript
 * Version: 1.0.4
 */

// Global state
let teamData = null;
let myPlayers = [];
let allPlayers = [];
let ws = null;
let charts = {};

// Get authentication
const token = localStorage.getItem('access_token');
const teamId = localStorage.getItem('team_id');

// Check authentication
if (!token || !teamId) {
    window.location.href = '/';
}

// API helper with token refresh
async function refreshAccessToken() {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
        return false;
    }
    
    try {
        const formData = new FormData();
        formData.append("refresh_token", refreshToken);
        
        const response = await fetch("/auth/refresh", {
            method: "POST",
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem("access_token", data.access_token);
            console.log("Token refreshed successfully");
            return true;
        }
    } catch (error) {
        console.error("Token refresh failed:", error);
    }
    
    return false;
}

async function api(url, options = {}) {
    // Always construct absolute HTTPS URLs for production
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        // Relative URL - construct absolute HTTPS URL
        url = `https://${window.location.host}${url}`;
    } else if (url.startsWith('http://')) {
        // Force HTTPS
        url = url.replace('http://', 'https://');
    }
    
    const currentToken = localStorage.getItem('access_token');
    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${currentToken}`
    };
    
    let response = await fetch(url, options);
    
    // If 401 Unauthorized, try to refresh token and retry
    if (response.status === 401) {
        console.log("Token expired, attempting refresh...");
        const refreshed = await refreshAccessToken();
        
        if (refreshed) {
            // Retry the request with new token
            const newToken = localStorage.getItem('access_token');
            options.headers = {
                ...options.headers,
                'Authorization': `Bearer ${newToken}`
            };
            response = await fetch(url, options);
        } else {
            // Refresh failed, redirect to login
            alert("Your session has expired. Please login again.");
            logout();
            return null;
        }
    }
    
    return response;
}

// Initialize dashboard
async function init() {
    console.log('Initializing Team Dashboard...');
    await loadTeamData();
    await loadMyPlayers();
    await loadAllPlayers();
    await loadAuctionStatus();
    connectWebSocket();
    initCharts();
    
    // Auto-refresh every 3 seconds (reduced from 5)
    setInterval(async () => {
        await loadTeamData();
        await loadAuctionStatus();
    }, 3000);
}

// Load team data
async function loadTeamData() {
    try {
        const res = await api(`/teams/${teamId}`);
        if (!res) return;
        
        teamData = await res.json();
        updateTeamOverview();
    } catch (error) {
        console.error('Error loading team data:', error);
    }
}

// Update team overview panel
function updateTeamOverview() {
    if (!teamData) return;
    
    // Team identity
    document.getElementById('team-name').textContent = teamData.name || 'Team';
    document.getElementById('team-username').textContent = `@${teamData.username || 'team'}`;
    
    // Team logo
    const logoContainer = document.getElementById('team-logo-container');
    if (teamData.logo_path && teamData.logo_path.trim()) {
        logoContainer.innerHTML = `<img src="${teamData.logo_path}" class="team-logo" alt="${teamData.name}">`;
    } else {
        const initial = (teamData.name || 'T')[0].toUpperCase();
        logoContainer.innerHTML = `<div class="team-logo-placeholder">${initial}</div>`;
    }
    
    // Statistics
    const budget = teamData.budget || 0;
    const spent = teamData.total_spent || 0;
    const remaining = budget - spent;
    const playersCount = teamData.players_count || 0;
    const highestPurchase = teamData.highest_purchase || 0;
    
    document.getElementById('total-budget').textContent = budget.toLocaleString();
    document.getElementById('total-spent').textContent = spent.toLocaleString();
    document.getElementById('remaining-purse').textContent = remaining.toLocaleString();
    document.getElementById('players-count').textContent = playersCount;
    document.getElementById('highest-purchase').textContent = highestPurchase.toLocaleString();
    
    // Purse progress bar
    const percentage = budget > 0 ? (remaining / budget) * 100 : 0;
    document.getElementById('purse-progress-bar').style.width = percentage + '%';
    document.getElementById('purse-percentage').textContent = percentage.toFixed(1);
    
    // Change color based on remaining budget
    const progressBar = document.getElementById('purse-progress-bar');
    if (percentage < 20) {
        progressBar.style.background = 'linear-gradient(90deg, #ef4444, #dc2626)';
        // Show critical budget alert
        if (!window.budgetAlertShown20) {
            showToast('Budget Alert!', `Only ${percentage.toFixed(1)}% of budget remaining (₹${remaining.toLocaleString()})`, 'error');
            window.budgetAlertShown20 = true;
        }
    } else if (percentage < 50) {
        progressBar.style.background = 'linear-gradient(90deg, #f59e0b, #d97706)';
        // Show warning budget alert
        if (!window.budgetAlertShown50) {
            showToast('Budget Warning', `${percentage.toFixed(1)}% of budget remaining (₹${remaining.toLocaleString()})`, 'warning');
            window.budgetAlertShown50 = true;
        }
    } else {
        progressBar.style.background = 'linear-gradient(90deg, #10b981, #667eea)';
    }
}

// Load auction status and current player
async function loadAuctionStatus() {
    try {
        const res = await api('/auction/status');
        if (!res) return;
        
        const status = await res.json();
        
        if (status.active && status.current_player_id) {
            await loadLivePlayer(status.current_player_id);
        } else {
            showNoAuction();
        }
    } catch (error) {
        console.error('Error loading auction status:', error);
        showNoAuction();
    }
}

// Load live player details
async function loadLivePlayer(playerId) {
    try {
        const res = await api(`/players/${playerId}`);
        if (!res) return;
        
        const player = await res.json();
        displayLivePlayer(player);
    } catch (error) {
        console.error('Error loading live player:', error);
    }
}

// Display live player
function displayLivePlayer(player) {
    const statusBadge = document.getElementById('live-status-badge');
    statusBadge.innerHTML = '<div class="live-badge"><i class="bi bi-circle-fill"></i> LIVE NOW</div>';
    
    const content = document.getElementById('auction-content');
    
    // Player image
    let playerImage = '';
    if (player.image_path) {
        playerImage = `<img src="${player.image_path}" class="player-image" alt="${player.name}" onerror="this.onerror=null; this.outerHTML='<div class=\\'player-image-placeholder\\'><i class=\\'bi bi-person-fill\\'></i></div>';">`;
    } else {
        playerImage = '<div class="player-image-placeholder"><i class="bi bi-person-fill"></i></div>';
    }
    
    // Current highest bid
    const currentBid = player.final_bid || player.base_price || 0;
    const leadingTeam = player.final_team ? 'You' : 'No bids yet';
    
    // Check if team can bid
    const canBid = teamData && (teamData.budget - teamData.total_spent) > currentBid;
    const isOwnPlayer = player.final_team === teamId;
    
    content.innerHTML = `
        <div class="player-showcase">
            <div class="player-image-container">
                ${playerImage}
            </div>
            <div class="player-details">
                <h3 class="player-name">${player.name}</h3>
                <div class="player-meta">
                    <span class="meta-badge role">
                        <i class="bi bi-trophy-fill"></i> ${player.role || 'Player'}
                    </span>
                    ${player.category ? `<span class="meta-badge category">
                        <i class="bi bi-tag-fill"></i> ${player.category}
                    </span>` : ''}
                </div>
                <div class="bid-info">
                    <div class="bid-info-item">
                        <div class="bid-info-label">Base Price</div>
                        <div class="bid-info-value">₹${(player.base_price || 0).toLocaleString()}</div>
                    </div>
                    <div class="bid-info-item">
                        <div class="bid-info-label">Current Bid</div>
                        <div class="bid-info-value">₹${currentBid.toLocaleString()}</div>
                    </div>
                    <div class="bid-info-item">
                        <div class="bid-info-label">Leading Team</div>
                        <div class="bid-info-value">${isOwnPlayer ? '🎯 You' : leadingTeam}</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="bid-controls">
            <div class="bid-input-group">
                <input 
                    type="number" 
                    class="bid-input" 
                    id="bid-amount" 
                    placeholder="Enter bid amount"
                    min="${currentBid + 50}"
                    step="50"
                    value="${currentBid + 50}"
                    onkeypress="if(event.key === 'Enter') { event.preventDefault(); placeBid('${player._id}', event); }"
                    ${!canBid || isOwnPlayer ? 'disabled' : ''}
                >
            </div>
            
            <!-- Quick Bid Presets for Mobile -->
            <div class="quick-bid-presets">
                <button class="quick-bid-btn" onclick="setQuickBid(${currentBid + 100})" ${!canBid || isOwnPlayer ? 'disabled' : ''}>
                    +100
                </button>
                <button class="quick-bid-btn" onclick="setQuickBid(${currentBid + 500})" ${!canBid || isOwnPlayer ? 'disabled' : ''}>
                    +500
                </button>
                <button class="quick-bid-btn" onclick="setQuickBid(${currentBid + 1000})" ${!canBid || isOwnPlayer ? 'disabled' : ''}>
                    +1K
                </button>
                <button class="quick-bid-btn" onclick="setQuickBid(${currentBid + 5000})" ${!canBid || isOwnPlayer ? 'disabled' : ''}>
                    +5K
                </button>
            </div>
            
            <button 
                type="button"
                class="bid-button" 
                onclick="placeBid('${player._id}')"
                ${!canBid || isOwnPlayer ? 'disabled' : ''}
            >
                <i class="bi bi-hammer"></i>
                ${isOwnPlayer ? 'You are Leading' : canBid ? 'Place Bid' : 'Insufficient Budget'}
            </button>
        </div>
        
        ${!canBid && !isOwnPlayer ? `
            <div class="alert alert-warning mt-3">
                <i class="bi bi-exclamation-triangle-fill"></i>
                Insufficient budget to bid on this player. Current bid: ₹${currentBid.toLocaleString()}, 
                Your remaining: ₹${(teamData.budget - teamData.total_spent).toLocaleString()}
            </div>
        ` : ''}
    `;
}

// Show no auction message
function showNoAuction() {
    const statusBadge = document.getElementById('live-status-badge');
    statusBadge.innerHTML = '<span class="badge bg-secondary">Auction Paused</span>';
    
    const content = document.getElementById('auction-content');
    content.innerHTML = `
        <div class="no-auction">
            <i class="bi bi-pause-circle"></i>
            <h4>No Active Auction</h4>
            <p>Waiting for admin to start the next player auction...</p>
        </div>
    `;
}

// Place bid
async function placeBid(playerId, event) {
    // Prevent any default behavior
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    const bidAmount = parseInt(document.getElementById('bid-amount').value);
    
    if (!bidAmount || bidAmount <= 0) {
        showToast('Invalid Bid', 'Please enter a valid bid amount', 'error');
        return;
    }
    
    // Validate budget
    const remaining = teamData.budget - teamData.total_spent;
    if (bidAmount > remaining) {
        showToast('Insufficient Budget', `You only have ₹${remaining.toLocaleString()} remaining`, 'error');
        return;
    }
    
    try {
        const res = await api('/auction/bid', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                player_id: playerId,
                team_id: teamId,  // Added team_id
                bid_amount: bidAmount
            })
        });
        
        if (!res) return;
        
        const data = await res.json();
        
        if (res.ok && data.ok) {
            showToast('Bid Placed!', `Your bid of ₹${bidAmount.toLocaleString()} has been placed`, 'success');
            await loadTeamData();
            await loadAuctionStatus();
        } else {
            showToast('Bid Failed', data.detail || 'Failed to place bid', 'error');
        }
    } catch (error) {
        console.error('Error placing bid:', error);
        showToast('Error', 'Failed to place bid. Please try again.', 'error');
    }
}

// Load my players
async function loadMyPlayers() {
    try {
        const res = await api(`/players?status=sold`);
        if (!res) return;
        
        const data = await res.json();
        const players = data.players || data;
        
        console.log('All sold players:', players.length);
        console.log('Team ID from localStorage:', teamId);
        
        // Filter only this team's players
        myPlayers = players.filter(p => {
            console.log(`Player ${p.name}: final_team=${p.final_team}, matches=${p.final_team === teamId}`);
            return p.final_team === teamId;
        });
        
        console.log('My players after filter:', myPlayers.length, myPlayers);
        
        displayMyPlayers();
        updateStatistics();
    } catch (error) {
        console.error('Error loading my players:', error);
    }
}

// Display my players
function displayMyPlayers() {
    const grid = document.getElementById('my-players-grid');
    
    if (myPlayers.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-inbox"></i>
                <h4>No Players Yet</h4>
                <p>Start bidding to build your squad!</p>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = myPlayers.map(player => createPlayerCard(player, true)).join('');
}

// Sort my players
function sortMyPlayers() {
    const sortBy = document.getElementById('my-players-sort').value;
    
    switch(sortBy) {
        case 'price-desc':
            myPlayers.sort((a, b) => (b.final_bid || 0) - (a.final_bid || 0));
            break;
        case 'price-asc':
            myPlayers.sort((a, b) => (a.final_bid || 0) - (b.final_bid || 0));
            break;
        case 'name':
            myPlayers.sort((a, b) => a.name.localeCompare(b.name));
            break;
        case 'role':
            myPlayers.sort((a, b) => (a.role || '').localeCompare(b.role || ''));
            break;
    }
    
    displayMyPlayers();
}

// Load all players
async function loadAllPlayers() {
    try {
        const res = await api('/players');
        if (!res) return;
        
        const data = await res.json();
        allPlayers = data.players || data;
        
        filterPlayers();
    } catch (error) {
        console.error('Error loading all players:', error);
    }
}

// Filter players
function filterPlayers() {
    const search = document.getElementById('player-search').value.toLowerCase();
    const role = document.getElementById('role-filter').value;
    const category = document.getElementById('category-filter').value;
    const status = document.getElementById('status-filter').value;
    
    let filtered = allPlayers.filter(player => {
        // HIDE SOLD PLAYERS - they shouldn't appear in available players list
        if (player.status === 'sold') {
            return false;
        }
        
        const matchSearch = !search || player.name.toLowerCase().includes(search);
        const matchRole = !role || player.role === role;
        const matchCategory = !category || player.category === category;
        const matchStatus = !status || player.status === status;
        
        return matchSearch && matchRole && matchCategory && matchStatus;
    });
    
    const grid = document.getElementById('all-players-grid');
    
    if (filtered.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-search"></i>
                <h4>No Players Found</h4>
                <p>Try adjusting your filters</p>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = filtered.map(player => createPlayerCard(player, false)).join('');
}

// Create player card HTML
function createPlayerCard(player, isOwned) {
    const defaultImg = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="280" height="220"%3E%3Crect fill="%230a0a0a" width="280" height="220"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="80" fill="%23ffd700"%3E👤%3C/text%3E%3C/svg%3E';
    
    // Handle image path - accept both Cloudinary URLs and local paths
    let imageSrc = defaultImg;
    if (player.image_path) {
        if (player.image_path.startsWith('http') || player.image_path.includes('/static/uploads/players/')) {
            imageSrc = player.image_path;
        }
    }
    
    const price = isOwned 
        ? '₹' + (player.final_bid || 0).toLocaleString()
        : player.status === 'sold'
        ? '₹' + (player.final_bid || 0).toLocaleString()
        : 'Base: ₹' + (player.base_price || 0).toLocaleString();
    
    const statusClass = player.status === 'sold' ? 'status-sold' : player.status === 'unsold' ? 'status-unsold' : 'status-available';
    const statusText = (player.status || 'available').toUpperCase();
    
    const roleInfo = (player.role || 'Player') + ' &bull; ' + (player.category || 'N/A');
    const teamInfo = player.team_name && !isOwned ? '<div class="player-card-info" style="color: #00d4ff;">Team: ' + player.name + '</div>' : '';
    
    return '<div class="player-card">' +
            '<img src="' + imageSrc + '" class="player-card-img" alt="' + player.name + '">' +
            '<div class="player-card-name">' + player.name + '</div>' +
            '<div class="player-card-info">' + roleInfo + '</div>' +
            '<div class="player-card-price">' + price + '</div>' +
            teamInfo +
            '<span class="status-badge ' + statusClass + '">' + statusText + '</span>' +
        '</div>';
}

// Initialize charts
function initCharts() {
    // Role spending chart
    const roleCtx = document.getElementById('role-chart');
    if (roleCtx) {
        charts.role = new Chart(roleCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: ['#667eea', '#764ba2', '#10b981', '#f59e0b', '#ef4444']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }
    
    // Category chart
    const categoryCtx = document.getElementById('category-chart');
    if (categoryCtx) {
        charts.category = new Chart(categoryCtx, {
            type: 'pie',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: ['#667eea', '#10b981', '#f59e0b']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }
    
    // Budget chart
    const budgetCtx = document.getElementById('budget-chart');
    if (budgetCtx) {
        charts.budget = new Chart(budgetCtx, {
            type: 'bar',
            data: {
                labels: ['Total Budget', 'Spent', 'Remaining'],
                datasets: [{
                    label: 'Amount (₹)',
                    data: [0, 0, 0],
                    backgroundColor: ['#667eea', '#ef4444', '#10b981']
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }
}

// Update statistics
function updateStatistics() {
    if (!teamData || myPlayers.length === 0) return;
    
    // Role spending
    const roleSpending = {};
    myPlayers.forEach(player => {
        const role = player.role || 'Unknown';
        roleSpending[role] = (roleSpending[role] || 0) + (player.final_bid || 0);
    });
    
    if (charts.role) {
        charts.role.data.labels = Object.keys(roleSpending);
        charts.role.data.datasets[0].data = Object.values(roleSpending);
        charts.role.update();
    }
    
    // Category distribution
    const categoryCount = {};
    myPlayers.forEach(player => {
        const category = player.category || 'Unknown';
        categoryCount[category] = (categoryCount[category] || 0) + 1;
    });
    
    if (charts.category) {
        charts.category.data.labels = Object.keys(categoryCount);
        charts.category.data.datasets[0].data = Object.values(categoryCount);
        charts.category.update();
    }
    
    // Budget overview
    if (charts.budget) {
        const budget = teamData.budget || 0;
        const spent = teamData.total_spent || 0;
        const remaining = budget - spent;
        
        charts.budget.data.datasets[0].data = [budget, spent, remaining];
        charts.budget.update();
    }
}

// WebSocket connection
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/auction/ws`;
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
    };
    
    ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);
        
        // Handle different event types
        switch(data.type) {
            case 'bid_placed':
                await loadTeamData();
                await loadAuctionStatus();
                
                // Show notification if outbid
                if (data.data && data.data.team_id !== teamId && data.data.previous_team_id === teamId) {
                    showToast('Outbid!', `You have been outbid on ${data.data.player_name}`, 'warning');
                    
                    // Browser notification if enabled
                    if (notificationPreferences.outbid && teamNotificationPermission === 'granted') {
                        showTeamNotification('🔔 Outbid!', {
                            body: `You have been outbid on ${data.data.player_name}`,
                            tag: 'outbid',
                            vibrate: [200, 100, 200, 100, 200]
                        });
                    }
                }
                break;
                
            case 'player_sold':
                await loadTeamData();
                await loadMyPlayers();
                await loadAuctionStatus();
                
                if (data.data && data.data.team_id === teamId) {
                    showToast('Player Acquired!', `You won ${data.data.player_name} for ₹${data.data.final_bid.toLocaleString()}`, 'success');
                    
                    // Browser notification if enabled
                    if (notificationPreferences.playerSold && teamNotificationPermission === 'granted') {
                        showTeamNotification('🎉 Player Acquired!', {
                            body: `You won ${data.data.player_name} for ₹${data.data.final_bid.toLocaleString()}`,
                            tag: 'player-sold',
                            vibrate: [300, 100, 300]
                        });
                    }
                }
                break;
                
            case 'player_unsold':
                await loadAuctionStatus();
                break;
                
            case 'player_live':
                await loadAuctionStatus();
                
                // Browser notification if enabled
                if (data.data && notificationPreferences.playerLive && teamNotificationPermission === 'granted') {
                    showTeamNotification('🔴 New Player Live', {
                        body: `${data.data.player_name} is now live for bidding`,
                        tag: 'player-live',
                        vibrate: [200]
                    });
                }
                break;
                
            case 'player_undo':
                // Handle undo event - refresh team data and players
                await loadTeamData();
                await loadMyPlayers();
                await loadAuctionStatus();
                
                if (data.data && data.data.team_id === teamId) {
                    showToast('Sale Undone', `${data.data.player_name} removed from your roster. ₹${data.data.refund_amount.toLocaleString()} refunded.`, 'warning');
                }
                break;
                
            case 'auction_reset':
                // Handle auction reset
                await loadTeamData();
                await loadMyPlayers();
                await loadAllPlayers();
                await loadAuctionStatus();
                showToast('Auction Reset', 'The auction has been reset by admin', 'warning');
                break;
                
            case 'chat_message':
                // Handle incoming chat message
                if (typeof handleChatMessage === 'function') {
                    handleChatMessage(data.data);
                }
                break;
                
            case 'auction_status':
                await loadAuctionStatus();
                
                // Check if wishlist player went live
                if (data.data && data.data.current_player_id && typeof handleWishlistPlayerLive === 'function') {
                    handleWishlistPlayerLive(data.data.current_player_id);
                }
                break;
                
            case 'timer_update':
                updateTeamAuctionTimer(data.data.seconds);
                break;
                
            case 'team_update':
                await loadTeamData();
                break;
        }
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting...');
        setTimeout(connectWebSocket, 3000);
    };
}

// Tab switching
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.custom-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    document.getElementById(tabName).classList.add('active');
    
    // Load data if needed
    if (tabName === 'statistics') {
        updateStatistics();
    }
}

// Toast notifications
function showToast(title, message, type = 'success') {
    const container = document.getElementById('toast-container');
    
    const icons = {
        success: 'bi-check-circle-fill',
        error: 'bi-x-circle-fill',
        warning: 'bi-exclamation-triangle-fill'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast-custom ${type}`;
    toast.innerHTML = `
        <i class="bi ${icons[type]} toast-icon ${type}"></i>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Logout
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('team_id');
    localStorage.removeItem('team_name');
    window.location.href = '/';
}

// Initialize on load
document.addEventListener('DOMContentLoaded', init);


// Auction Timer Display for Team Dashboard
let teamLastBeepSecond = -1;

function updateTeamAuctionTimer(seconds) {
    console.log('Team timer update:', seconds);
    const timerCard = document.getElementById('team-auction-timer-card');
    const timerDisplay = document.getElementById('team-auction-timer-display');
    const progressBar = document.getElementById('team-timer-progress-bar');
    
    console.log('Team timer elements:', {
        timerCard: !!timerCard,
        timerDisplay: !!timerDisplay,
        progressBar: !!progressBar
    });
    
    if (!timerCard || !timerDisplay || !progressBar) {
        console.error('Team timer elements not found!');
        return;
    }
    
    if (seconds > 0) {
        console.log('Showing team timer with', seconds, 'seconds');
        timerCard.style.display = 'block';
        
        // Format time
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        timerDisplay.textContent = `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        
        // Update progress - use 30 as max
        const percentage = Math.min(100, (seconds / 30) * 100);
        progressBar.style.width = percentage + '%';
        
        // Color changes
        if (seconds <= 5) {
            progressBar.classList.remove('bg-warning', 'bg-success');
            progressBar.classList.add('bg-danger');
            timerDisplay.style.color = '#ff4444';
            timerDisplay.style.animation = 'pulse 0.5s infinite';
        } else if (seconds <= 10) {
            progressBar.classList.remove('bg-success', 'bg-danger');
            progressBar.classList.add('bg-warning');
            timerDisplay.style.color = '#ffaa00';
            timerDisplay.style.animation = 'none';
        } else {
            progressBar.classList.remove('bg-warning', 'bg-danger');
            progressBar.classList.add('bg-success');
            timerDisplay.style.color = '#ffffff';
            timerDisplay.style.animation = 'none';
        }
        
        // Play beeps
        if (seconds <= 10 && seconds !== teamLastBeepSecond) {
            playTeamCountdownBeep(seconds);
            teamLastBeepSecond = seconds;
        }
        
        // Enable bid button when timer is running
        const bidButton = document.querySelector('.bid-button');
        if (bidButton) {
            bidButton.disabled = false;
        }
    } else {
        // Timer expired - disable bidding
        timerCard.style.display = 'none';
        teamLastBeepSecond = -1;
        
        // Disable bid button when timer expires
        const bidButton = document.querySelector('.bid-button');
        if (bidButton) {
            bidButton.disabled = true;
            bidButton.textContent = 'Auction Closed';
        }
        
        // Show message that auction is closing
        showToast('Auction Closed', 'Time expired! Auction is being finalized...', 'warning');
    }
}

function playTeamCountdownBeep(seconds) {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        if (seconds <= 3) {
            oscillator.frequency.value = 1200;
            gainNode.gain.value = 0.3;
        } else if (seconds <= 5) {
            oscillator.frequency.value = 900;
            gainNode.gain.value = 0.2;
        } else {
            oscillator.frequency.value = 600;
            gainNode.gain.value = 0.15;
        }
        
        oscillator.type = 'sine';
        oscillator.start();
        oscillator.stop(audioContext.currentTime + 0.1);
    } catch (error) {
        console.log('Audio not supported');
    }
}


/* ============================================================
    NOTIFICATION SYSTEM FOR TEAMS
    Version: 3.5.0
============================================================ */
let teamNotificationPermission = 'default';
let notificationPreferences = {
    outbid: true,
    playerSold: true,
    budgetWarning: true,
    playerLive: false
};

// Load notification preferences from localStorage
function loadNotificationPreferences() {
    const saved = localStorage.getItem('notification_preferences');
    if (saved) {
        try {
            notificationPreferences = JSON.parse(saved);
        } catch (e) {
            console.error('Error loading notification preferences:', e);
        }
    }
}

// Save notification preferences
function saveNotificationPreferences() {
    localStorage.setItem('notification_preferences', JSON.stringify(notificationPreferences));
}

// Request notification permission
async function requestTeamNotificationPermission() {
    if (!('Notification' in window)) {
        console.log('Browser does not support notifications');
        return false;
    }
    
    if (Notification.permission === 'granted') {
        teamNotificationPermission = 'granted';
        return true;
    }
    
    if (Notification.permission !== 'denied') {
        const permission = await Notification.requestPermission();
        teamNotificationPermission = permission;
        return permission === 'granted';
    }
    
    return false;
}

// Show team notification
function showTeamNotification(title, options = {}) {
    if (teamNotificationPermission !== 'granted') {
        console.log('Notification permission not granted');
        return;
    }
    
    const defaultOptions = {
        icon: '/static/logo.png',
        badge: '/static/badge.png',
        vibrate: [200, 100, 200],
        requireInteraction: false,
        ...options
    };
    
    try {
        const notification = new Notification(title, defaultOptions);
        
        // Auto-close after 6 seconds
        setTimeout(() => notification.close(), 6000);
        
        // Handle click - focus window
        notification.onclick = function(event) {
            event.preventDefault();
            window.focus();
            notification.close();
        };
        
        return notification;
    } catch (error) {
        console.error('Error showing notification:', error);
        return null;
    }
}

// Show notification settings modal
function showNotificationSettings() {
    const modal = document.createElement('div');
    modal.className = 'notification-settings-modal';
    
    const content = document.createElement('div');
    content.className = 'notification-settings-content';
    
    content.innerHTML = 
        '<h3>🔔 Notification Settings</h3>' +
        '<p class="text-muted">Choose which notifications you want to receive</p>' +
        
        '<div class="notification-option">' +
            '<label>' +
                '<input type="checkbox" id="notif-outbid" ' + (notificationPreferences.outbid ? 'checked' : '') + '>' +
                '<div><span style="font-size:16px;font-weight:600;display:block;margin-bottom:4px;">Outbid Alerts</span>' +
                '<small style="display:block;color:rgba(255,255,255,0.6);font-size:13px;">When another team outbids you</small></div>' +
            '</label>' +
        '</div>' +
        
        '<div class="notification-option">' +
            '<label>' +
                '<input type="checkbox" id="notif-player-sold" ' + (notificationPreferences.playerSold ? 'checked' : '') + '>' +
                '<div><span style="font-size:16px;font-weight:600;display:block;margin-bottom:4px;">Player Acquired</span>' +
                '<small style="display:block;color:rgba(255,255,255,0.6);font-size:13px;">When you successfully acquire a player</small></div>' +
            '</label>' +
        '</div>' +
        
        '<div class="notification-option">' +
            '<label>' +
                '<input type="checkbox" id="notif-budget-warning" ' + (notificationPreferences.budgetWarning ? 'checked' : '') + '>' +
                '<div><span style="font-size:16px;font-weight:600;display:block;margin-bottom:4px;">Budget Warnings</span>' +
                '<small style="display:block;color:rgba(255,255,255,0.6);font-size:13px;">When your budget is running low</small></div>' +
            '</label>' +
        '</div>' +
        
        '<div class="notification-option">' +
            '<label>' +
                '<input type="checkbox" id="notif-player-live" ' + (notificationPreferences.playerLive ? 'checked' : '') + '>' +
                '<div><span style="font-size:16px;font-weight:600;display:block;margin-bottom:4px;">New Player Live</span>' +
                '<small style="display:block;color:rgba(255,255,255,0.6);font-size:13px;">When a new player goes live for bidding</small></div>' +
            '</label>' +
        '</div>' +
        
        '<div class="notification-settings-actions">' +
            '<button class="btn btn-primary" onclick="saveNotificationSettings()">Save Settings</button>' +
            '<button class="btn btn-secondary" onclick="closeNotificationSettings()">Cancel</button>' +
        '</div>';
    
    modal.appendChild(content);
    document.body.appendChild(modal);
    
    // Close on background click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeNotificationSettings();
        }
    });
}

// Save notification settings
function saveNotificationSettings() {
    notificationPreferences.outbid = document.getElementById('notif-outbid').checked;
    notificationPreferences.playerSold = document.getElementById('notif-player-sold').checked;
    notificationPreferences.budgetWarning = document.getElementById('notif-budget-warning').checked;
    notificationPreferences.playerLive = document.getElementById('notif-player-live').checked;
    
    saveNotificationPreferences();
    closeNotificationSettings();
    showToast('Settings Saved', 'Notification preferences updated', 'success');
}

// Close notification settings
function closeNotificationSettings() {
    const modal = document.querySelector('.notification-settings-modal');
    if (modal) {
        modal.remove();
    }
}

// Expose functions globally
window.showNotificationSettings = showNotificationSettings;
window.saveNotificationSettings = saveNotificationSettings;
window.closeNotificationSettings = closeNotificationSettings;

// Initialize notifications
loadNotificationPreferences();
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(() => {
            requestTeamNotificationPermission();
        }, 3000);
    });
} else {
    setTimeout(() => {
        requestTeamNotificationPermission();
    }, 3000);
}


/* ============================================================
    QUICK BID PRESETS FOR MOBILE
    Version: 3.5.0
============================================================ */
function setQuickBid(amount) {
    const bidInput = document.getElementById('bid-amount');
    if (bidInput) {
        bidInput.value = amount;
        
        // Add haptic feedback animation
        bidInput.classList.add('haptic-feedback');
        setTimeout(() => {
            bidInput.classList.remove('haptic-feedback');
        }, 200);
        
        // Vibrate if supported
        if ('vibrate' in navigator) {
            navigator.vibrate(50);
        }
    }
}

// Expose function globally
window.setQuickBid = setQuickBid;
