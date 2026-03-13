/* ============================================================
    AUTH HELPERS
    
    Version: 5.4.1
    Changes:
    - Added graceful 403 error handling for analytics endpoints
    - Analytics tab auto-hides if all endpoints return 403
    - Activity logs and bid history show user-friendly messages on 403
    - Live monitor handles missing stats data gracefully
    - Eligible players dropdown handles 403 errors
    - Prevents JavaScript errors from undefined data
============================================================ */
console.log('Admin.js loaded!');
console.log('Access token:', localStorage.getItem("access_token") ? 'Present' : 'Missing');

function getAccess() { return localStorage.getItem("access_token"); }
function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    window.location.href = "/";
}

async function refreshAccessToken() {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
        console.warn("No refresh token available");
        return false;
    }
    
    try {
        const formData = new FormData();
        formData.append("refresh_token", refreshToken);
        
        console.log("Attempting to refresh token...");
        const response = await fetch("/auth/refresh", {
            method: "POST",
            body: formData
        });
        
        console.log("Refresh response status:", response.status);
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem("access_token", data.access_token);
            console.log("Token refreshed successfully");
            return true;
        } else {
            const errorText = await response.text();
            console.error("Token refresh failed:", response.status, errorText);
        }
    } catch (error) {
        console.error("Token refresh error:", error);
    }
    
    return false;
}

async function api(url, options = {}) {
    // Always construct absolute HTTPS URLs for production
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        // Relative URL - construct absolute HTTPS URL
        url = `https://${window.location.host}${url}`;
        console.log('Constructed HTTPS URL:', url);
    } else if (url.startsWith('http://')) {
        // Force HTTPS
        url = url.replace('http://', 'https://');
        console.log('Converted HTTP to HTTPS:', url);
    }
    
    const token = getAccess();
    options.headers = Object.assign(
        {},
        options.headers || {},
        token ? { Authorization: `Bearer ${token}` } : {}
    );
    
    let response = await fetch(url, options);
    
    // If 401 Unauthorized, try to refresh token and retry
    if (response.status === 401) {
        console.log("Token expired, attempting refresh...");
        const refreshed = await refreshAccessToken();
        
        if (refreshed) {
            // Retry the request with new token
            const newToken = getAccess();
            options.headers = Object.assign(
                {},
                options.headers || {},
                newToken ? { Authorization: `Bearer ${newToken}` } : {}
            );
            response = await fetch(url, options);
            
            // If still 401 after refresh, something is wrong
            if (response.status === 401) {
                console.error("Still unauthorized after token refresh");
                alert("Your session has expired. Please login again.");
                logout();
            }
        } else {
            // Refresh failed - but don't logout immediately, just warn
            console.warn("Token refresh failed, but continuing...");
            // Only logout if this is a critical endpoint
            if (url.includes('/admin/') || url.includes('/auction/')) {
                alert("Your session has expired. Please login again.");
                logout();
            }
        }
    }
    
    return response;
}

// Expose api function globally for admin_teams.js
window.api = api;

/* ============================================================
    LOAD AUCTION STATUS
============================================================ */
async function loadAuctionStatus() {
    try {
        const r = await api("/auction/status");
        
        // If unauthorized, redirect to home
        if (r.status === 401 || r.status === 403) {
            alert('Please login as admin first');
            window.location.href = "/";
            return;
        }
        
        const s = await r.json();
        const el = document.getElementById("auction-status");

        el.textContent = s.active ? "Auction is LIVE" : "Auction is NOT active";
        el.classList.toggle("alert-success", s.active);
        el.classList.toggle("alert-secondary", !s.active);
    } catch (error) {
        console.error('Error loading auction status:', error);
    }
}

/* ============================================================
    START / STOP AUCTION
============================================================ */
const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");

if (btnStart) {
    btnStart.addEventListener("click", async () => {
        console.log('Start auction clicked');
        try {
            const res = await api("/auction/start", { method: "POST" });
            const data = await res.json();
            alert(data.message || "Auction started");
            loadAuctionStatus();
        } catch (error) {
            console.error('Error starting auction:', error);
            alert('Error starting auction: ' + error.message);
        }
    });
} else {
    console.error('btn-start element not found!');
}

if (btnStop) {
    btnStop.addEventListener("click", async () => {
        console.log('Stop auction clicked');
        try {
            const res = await api("/auction/stop", { method: "POST" });
            const data = await res.json();
            alert(data.message || "Auction stopped");
            loadAuctionStatus();
        } catch (error) {
            console.error('Error stopping auction:', error);
            alert('Error stopping auction: ' + error.message);
        }
    });
} else {
    console.error('btn-stop element not found!');
}

/* ============================================================
    LOAD PENDING PLAYERS (SET BASE PRICE)
============================================================ */
async function loadPendingPlayers() {
    const res = await api("/admin/players/pending");
    const data = await res.json();

    const list = document.getElementById("admin-pending-list");
    list.innerHTML = "";

    (data.players || []).forEach(p => {
        const li = document.createElement("li");
        li.className = "list-group-item d-flex justify-content-between flex-wrap";

        li.innerHTML = `
            <div><strong>${p.name}</strong> (${p.affiliation_role || "-"})</div>
            <div class="input-group" style="max-width:240px;">
                <span class="input-group-text">₹</span>
                <input type="number" min="1" class="form-control" id="bp-${p._id}" placeholder="Base Price">
                <button class="btn btn-primary">Set</button>
            </div>
        `;

        li.querySelector("button").onclick = async () => {
            const price = Number(document.getElementById(`bp-${p._id}`).value);
            if (!price) return alert("Enter valid price");

            const r = await api(`/admin/player/${p._id}/base-price`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ price })
            });

            const d = await r.json();
            if (!r.ok) return alert(d.detail || "Failed");

            alert("Base price set!");
            loadPendingPlayers();
        };

        list.appendChild(li);
    });
}

/* ============================================================
    TEAM MANAGEMENT - Moved to admin_teams.js
============================================================ */
// All team management functions are now in admin_teams.js
// This includes: loadTeams(), openTeamModal(), editTeam(), saveTeam(), deleteTeam()

/* ============================================================
    LOAD PLAYERS FOR ADMIN (BID + SOLD) WITH FILTERING
============================================================ */
let allAdminPlayers = [];

async function loadPlayersAdmin() {
    console.log("Loading players for admin...");
    const r = await api("/players?include_unapproved=true");
    const data = await r.json();
    console.log("Players loaded:", data);
    allAdminPlayers = data.players || data;
    console.log("Total players:", allAdminPlayers.length);
    
    // Update stats
    updatePlayerStats();
    
    renderAdminPlayerTabs();
    loadTeamsIntoDropdowns();
}

function updatePlayerStats() {
    const total = allAdminPlayers.length;
    const sold = allAdminPlayers.filter(p => p.status === 'sold').length;
    const unsold = allAdminPlayers.filter(p => p.status === 'unsold').length;
    const available = allAdminPlayers.filter(p => p.status === 'available' || !p.status).length;
    const batsmen = allAdminPlayers.filter(p => p.role && p.role.toLowerCase().includes('bats')).length;
    const bowlers = allAdminPlayers.filter(p => p.role && p.role.toLowerCase().includes('bowl')).length;
    
    document.getElementById('stats-total-players').textContent = total;
    document.getElementById('stats-sold-players').textContent = sold;
    document.getElementById('stats-unsold-players').textContent = unsold;
    document.getElementById('stats-available-players').textContent = available;
    document.getElementById('stats-batsmen').textContent = batsmen;
    document.getElementById('stats-bowlers').textContent = bowlers;
}

// Apply admin filters
function getFilteredAdminPlayers() {
    const searchName = document.getElementById('admin-search-name')?.value.toLowerCase() || '';
    const filterRole = document.getElementById('admin-filter-role')?.value.toLowerCase() || '';
    const filterCategory = document.getElementById('admin-filter-category')?.value.toLowerCase() || '';
    const filterStatus = document.getElementById('admin-filter-status')?.value.toLowerCase() || '';
    const showSold = document.getElementById('admin-show-sold')?.checked || false;

    return allAdminPlayers.filter(player => {
        // When "Show Sold Players" is CHECKED: Show ONLY sold players
        // When UNCHECKED: Show only available and unsold players (hide sold)
        if (showSold) {
            // Show ONLY sold players
            if (player.status !== 'sold') {
                return false;
            }
        } else {
            // Hide sold players (show available and unsold)
            if (player.status === 'sold') {
                return false;
            }
        }
        
        const matchName = !searchName || player.name.toLowerCase().includes(searchName);
        const matchRole = !filterRole || (player.role && player.role.toLowerCase().includes(filterRole));
        const matchCategory = !filterCategory || (player.category && player.category.toLowerCase() === filterCategory);
        const matchStatus = !filterStatus || ((player.status || 'available').toLowerCase() === filterStatus);
        return matchName && matchRole && matchCategory && matchStatus;
    });
}

// Render players in a specific tab - OPTIMIZED
function renderAdminPlayersInTab(players, containerId) {
    const wrap = document.getElementById(containerId);
    if (!wrap) return;
    
    if (players.length === 0) {
        wrap.innerHTML = '<div class="text-center text-muted py-4" style="grid-column: 1/-1;">No players found</div>';
        return;
    }

    const defaultImg = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="280" height="220"%3E%3Crect fill="%230a0a0a" width="280" height="220"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="80" fill="%23ffd700"%3E👤%3C/text%3E%3C/svg%3E';

    // Use DocumentFragment for better performance
    const fragment = document.createDocumentFragment();

    players.forEach(p => {
        // Handle image path - use Cloudinary URL or local path
        let imageSrc = defaultImg;
        if (p.image_path) {
            // Accept both Cloudinary URLs and local paths
            if (p.image_path.startsWith('http') || p.image_path.includes('/static/uploads/players/')) {
                imageSrc = p.image_path;
            }
        }
        
        const statusClass = `status-${p.status || 'available'}`;
        const price = p.status === 'sold' ? `₹${(p.final_bid || 0).toLocaleString()}` : `Base: ₹${(p.base_price || 0).toLocaleString()}`;
        const suggested = p.final_bid || p.price ? (p.final_bid || p.price) + 50 : (p.base_price || 100);

        const card = document.createElement("div");
        card.className = "player-card-admin";
        card.style.position = "relative";

        card.innerHTML = `
            <span class="status-badge-admin ${statusClass}">${(p.status || 'available').toUpperCase()}</span>
            <img src="${imageSrc}" class="player-card-admin-img" alt="${p.name}" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
            <div class="player-card-admin-img" style="display:none; align-items:center; justify-content:center; background:#0a0a0a; font-size:64px; color:#ffd700;">👤</div>
            <div class="player-card-admin-body">
                <div class="player-card-admin-name">${p.name}</div>
                <div class="player-card-admin-info">
                    ${p.role ? `<span class="badge bg-primary me-1">${p.role}</span>` : ''}
                    ${p.category ? `<span class="badge bg-secondary">${p.category}</span>` : ''}
                </div>
                <div class="player-card-admin-price">${price}</div>
                ${p.team_name ? `<div class="player-card-admin-info" style="color: #00d4ff;">Team: ${p.team_name}</div>` : ''}
                
                <div class="player-card-admin-actions">
                    <input type="number" class="form-control form-control-sm" id="bid-${p._id}" value="${suggested}" placeholder="Bid">
                </div>
                <div class="player-card-admin-actions mt-2">
                    <select id="team-${p._id}" class="form-select form-select-sm"></select>
                </div>
                <div class="player-card-admin-actions mt-2">
                    <button class="btn btn-sm btn-primary flex-1" onclick="placeBid('${p._id}')">
                        <i class="fas fa-gavel"></i> Bid
                    </button>
                    <button class="btn btn-sm btn-success flex-1" onclick="markSold('${p._id}')">
                        <i class="fas fa-check"></i> SOLD
                    </button>
                </div>
                <div class="player-card-admin-actions mt-2">
                    <button class="btn btn-sm btn-danger w-100" onclick="deletePlayer('${p._id}', '${p.name.replace(/'/g, "\\'")}')">
                        <i class="fas fa-trash"></i> Delete Player
                    </button>
                </div>
            </div>
        `;

        fragment.appendChild(card);
    });
    
    // Clear and append all at once for better performance
    wrap.innerHTML = '';
    wrap.appendChild(fragment);
    
    // Reload team dropdowns after rendering
    loadTeamsIntoDropdowns();
}

// Render all admin tabs
function renderAdminPlayerTabs() {
    const filtered = getFilteredAdminPlayers();
    
    // All players
    renderAdminPlayersInTab(filtered, 'admin-all-players-list');
    
    // Batsmen
    const batsmen = filtered.filter(p => p.role && p.role.toLowerCase().includes('bats'));
    renderAdminPlayersInTab(batsmen, 'admin-batsman-players-list');
    
    // Bowlers
    const bowlers = filtered.filter(p => p.role && p.role.toLowerCase().includes('bowl'));
    renderAdminPlayersInTab(bowlers, 'admin-bowler-players-list');
    
    // All-Rounders
    const allrounders = filtered.filter(p => p.role && p.role.toLowerCase().includes('round'));
    renderAdminPlayersInTab(allrounders, 'admin-allrounder-players-list');
    
    // Wicketkeepers
    const wicketkeepers = filtered.filter(p => p.role && p.role.toLowerCase().includes('keeper'));
    renderAdminPlayersInTab(wicketkeepers, 'admin-wicketkeeper-players-list');
}

/* Populate each player's dropdown */
async function loadTeamsIntoDropdowns() {
    const r = await api("/teams/");
    const teams = await r.json();

    document.querySelectorAll("[id^='team-']").forEach(sel => {
        sel.innerHTML = teams
            .map(t => `<option value="${t._id}">${t.name}</option>`)
            .join("");
    });
}

/* ============================================================
    SELECTED PLAYER INFO PANEL
============================================================ */
function showSelectedPlayerInfo(row) {
    const box = document.getElementById("selected-player-info-admin");
    box.classList.remove("d-none");

    box.querySelector(".selected-player-name").textContent = row.dataset.name;
    box.querySelector(".selected-player-category").textContent = row.dataset.category;
    box.querySelector(".selected-player-base-price").textContent = row.dataset.basePrice;
    box.querySelector(".selected-player-status").textContent = row.dataset.status;
    box.querySelector(".selected-player-final-bid").textContent = row.dataset.finalBid;
    box.querySelector(".selected-player-team").textContent = row.dataset.team;

    box.querySelector(".selected-player-age").textContent = row.dataset.age;
    box.querySelector(".selected-player-batting").textContent = row.dataset.batting;
    box.querySelector(".selected-player-bowling").textContent = row.dataset.bowling;
    box.querySelector(".selected-player-affiliation").textContent = row.dataset.affiliation;
    box.querySelector(".selected-player-bio").textContent = row.dataset.bio;
}

/* ============================================================
    BID
============================================================ */
async function placeBid(pid) {
    const teamId = document.getElementById(`team-${pid}`).value;
    const amount = Number(document.getElementById(`bid-${pid}`).value);

    if (!amount) return alert("Enter amount");
    
    console.log("Placing bid:", { player_id: pid, team_id: teamId, bid_amount: amount });

    const r = await api("/auction/bid", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            player_id: pid,
            team_id: teamId,
            bid_amount: amount
        })
    });
    
    if (!r.ok) {
        const errorText = await r.text();
        console.error("Bid error:", r.status, errorText);
        try {
            const errorJson = JSON.parse(errorText);
            alert(errorJson.detail || errorJson.message || "Bid failed");
        } catch {
            alert(`Bid failed: ${r.status} ${r.statusText}`);
        }
        return;
    }

    const d = await r.json();
    alert(d.message || d.detail || "Bid complete");
    loadPlayersAdmin();
    // Teams will auto-refresh in admin_teams.js if needed
}

/* ============================================================
    SOLD
============================================================ */
async function markSold(pid) {
    if (!confirm("Mark this player as SOLD?")) return;

    const r = await api(`/auction/sold/${pid}`, { method: "POST" });
    
    if (!r.ok) {
        const errorText = await r.text();
        console.error("Mark sold error:", r.status, errorText);
        try {
            const errorJson = JSON.parse(errorText);
            alert(errorJson.detail || errorJson.message || "Failed to mark as sold");
        } catch {
            alert(`Failed: ${r.status} ${r.statusText}`);
        }
        return;
    }
    
    const d = await r.json();
    alert(d.message || "Player marked as SOLD");
    loadPlayersAdmin();
}

/* ============================================================
    PLAYER APPROVAL SYSTEM
============================================================ */

async function loadPendingApprovals() {
    try {
        const res = await api("/admin/players/pending-approval");
        const data = await res.json();
        
        const container = document.getElementById("pending-approvals-container");
        
        if (!data.ok || !data.players || data.players.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">No pending approvals</p>';
            return;
        }
        
        let html = '<div class="table-responsive"><table class="table table-hover">';
        html += '<thead><tr>';
        html += '<th>Image</th><th>Name</th><th>Role</th><th>Category</th>';
        html += '<th>Base Price</th><th>Registered</th><th>Actions</th>';
        html += '</tr></thead><tbody>';
        
        data.players.forEach(player => {
            const imgSrc = player.image_path || 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%230a0a0a" width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="80" fill="%23ffd700"%3E👤%3C/text%3E%3C/svg%3E';
            const regDate = player.created_at ? new Date(player.created_at).toLocaleDateString() : 'N/A';
            const basePrice = player.base_price ? `₹${player.base_price.toLocaleString()}` : 'Not Set';
            
            html += '<tr>';
            html += `<td><img src="${imgSrc}" alt="${player.name}" style="width:50px;height:50px;object-fit:cover;border-radius:5px;" onerror="this.onerror=null; this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22%3E%3Crect fill=%22%23ddd%22 width=%22100%22 height=%22100%22/%3E%3Ctext fill=%22%23999%22 font-family=%22Arial%22 font-size=%2240%22 x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22%3E${player.name.charAt(0).toUpperCase()}%3C/text%3E%3C/svg%3E';"></td>`;
            html += `<td><strong>${player.name}</strong></td>`;
            html += `<td><span class="badge bg-info">${player.role || 'N/A'}</span></td>`;
            html += `<td><span class="badge bg-secondary">${player.category || 'N/A'}</span></td>`;
            html += `<td>${basePrice}</td>`;
            html += `<td><small>${regDate}</small></td>`;
            html += `<td>
                <button onclick="approvePlayer('${player._id}')" class="btn btn-success btn-sm me-1">
                    ✓ Approve
                </button>
                <button onclick="rejectPlayer('${player._id}')" class="btn btn-danger btn-sm">
                    ✗ Reject
                </button>
            </td>`;
            html += '</tr>';
        });
        
        html += '</tbody></table></div>';
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading pending approvals:', error);
        document.getElementById("pending-approvals-container").innerHTML = 
            '<p class="text-danger">Error loading pending approvals</p>';
    }
}

async function approvePlayer(playerId) {
    if (!confirm('Approve this player registration?')) return;
    
    try {
        const res = await api(`/admin/players/${playerId}/approve`, { method: "POST" });
        const data = await res.json();
        
        if (!res.ok) {
            alert(data.detail || 'Failed to approve player');
            return;
        }
        
        alert(data.message || 'Player approved successfully');
        loadPendingApprovals();
        loadPlayersAdmin(); // Refresh player list
        
    } catch (error) {
        console.error('Error approving player:', error);
        alert('Error approving player: ' + error.message);
    }
}

async function rejectPlayer(playerId) {
    if (!confirm('Reject this player registration? This will mark the player as rejected.')) return;
    
    try {
        const res = await api(`/admin/players/${playerId}/reject`, { method: "POST" });
        const data = await res.json();
        
        if (!res.ok) {
            alert(data.detail || 'Failed to reject player');
            return;
        }
        
        alert(data.message || 'Player rejected');
        loadPendingApprovals();
        
    } catch (error) {
        console.error('Error rejecting player:', error);
        alert('Error rejecting player: ' + error.message);
    }
}

/* ============================================================
    LIVE AUCTION CONTROLLER
============================================================ */

let currentLivePlayerId = null;

async function loadCurrentLivePlayer() {
    try {
        const res = await api("/admin/auction/live-player");
        const data = await res.json();
        
        const nameSpan = document.getElementById("live-player-name");
        const endContainer = document.getElementById("end-live-auction-container");
        
        if (data.ok && data.live_player) {
            nameSpan.textContent = data.live_player.name;
            nameSpan.parentElement.classList.remove('alert-info');
            nameSpan.parentElement.classList.add('alert-success');
            currentLivePlayerId = data.live_player._id;
            endContainer.style.display = 'block';
        } else {
            nameSpan.textContent = 'None';
            nameSpan.parentElement.classList.remove('alert-success');
            nameSpan.parentElement.classList.add('alert-info');
            currentLivePlayerId = null;
            endContainer.style.display = 'none';
        }
        
        // Load eligible players for dropdown
        await loadEligiblePlayers();
        
    } catch (error) {
        console.error('Error loading current live player:', error);
    }
}

async function loadEligiblePlayers() {
    try {
        const res = await api("/admin/auction/eligible-players");
        
        if (!res.ok) {
            if (res.status === 403) {
                console.log('Eligible players endpoint not accessible (403)');
                const select = document.getElementById("eligible-players-select");
                if (select) {
                    select.innerHTML = '<option value="">Access denied</option>';
                    select.disabled = true;
                }
                return;
            }
            throw new Error(`HTTP ${res.status}`);
        }
        
        const data = await res.json();
        
        const select = document.getElementById("eligible-players-select");
        select.innerHTML = '<option value="">-- Select a player --</option>';
        select.disabled = false;
        
        if (data.ok && data.players && data.players.length > 0) {
            data.players.forEach(player => {
                const option = document.createElement('option');
                option.value = player._id;
                option.textContent = `${player.name} (${player.role}) - ₹${player.base_price || 0}`;
                select.appendChild(option);
            });
        } else {
            select.innerHTML = '<option value="">No eligible players available</option>';
        }
        
    } catch (error) {
        console.error('Error loading eligible players:', error);
        const select = document.getElementById("eligible-players-select");
        if (select) {
            select.innerHTML = '<option value="">Error loading players</option>';
            select.disabled = true;
        }
    }
}

async function setLivePlayerFromSelect() {
    const select = document.getElementById("eligible-players-select");
    const playerId = select.value;
    
    if (!playerId) {
        alert('Please select a player first');
        return;
    }
    
    const playerName = select.options[select.selectedIndex].text;
    
    if (!confirm(`Set "${playerName}" to live auction?`)) return;
    
    try {
        const res = await api(`/admin/auction/set-live-player/${playerId}`, { method: "POST" });
        const data = await res.json();
        
        if (!res.ok) {
            alert(data.detail || 'Failed to set player live');
            return;
        }
        
        alert(data.message || 'Player is now live in auction');
        loadCurrentLivePlayer();
        loadLiveMonitor(); // Refresh live monitor
        
    } catch (error) {
        console.error('Error setting live player:', error);
        alert('Error setting live player: ' + error.message);
    }
}

async function endCurrentLivePlayer() {
    if (!currentLivePlayerId) {
        alert('No live player to end');
        return;
    }
    
    if (!confirm('End the current live auction?')) return;
    
    try {
        const res = await api(`/admin/auction/end-live-player/${currentLivePlayerId}`, { method: "POST" });
        const data = await res.json();
        
        if (!res.ok) {
            alert(data.detail || 'Failed to end live auction');
            return;
        }
        
        alert(data.message || 'Live auction ended');
        loadCurrentLivePlayer();
        loadPlayersAdmin(); // Refresh player list
        loadLiveMonitor(); // Refresh live monitor
        
    } catch (error) {
        console.error('Error ending live player:', error);
        alert('Error ending live player: ' + error.message);
    }
}

/* ============================================================
    INITIAL LOAD
============================================================ */
// WebSocket connection for real-time updates
let adminWs = null;

function connectAdminWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/auction/ws`;
    adminWs = new WebSocket(wsUrl);
    
    adminWs.onopen = () => {
        console.log('Admin WebSocket connected');
    };
    
    adminWs.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Admin WebSocket message:', data);
        
        // Handle different event types
        switch(data.type) {
            case 'bid_placed':
                loadLiveMonitor();
                loadAnalytics();
                break;
            case 'player_live':
                loadCurrentLivePlayer();
                loadLiveMonitor();
                break;
            case 'player_sold':
            case 'player_unsold':
                loadCurrentLivePlayer();
                loadLiveMonitor();
                loadAnalytics();
                loadPlayersAdmin();
                break;
            case 'player_undo':
                // Handle undo event
                loadPlayersAdmin();
                if (typeof loadTeams === 'function') {
                    loadTeams();
                }
                loadLiveMonitor();
                loadAnalytics();
                // Show notification
                if (data.data) {
                    alert(`🔄 UNDO: ${data.data.player_name} restored to auction. ₹${data.data.refund_amount.toLocaleString()} refunded to ${data.data.team_name}`);
                }
                break;
            case 'auction_status':
                loadAuctionStatus();
                break;
            case 'team_update':
                if (typeof loadTeams === 'function') {
                    loadTeams();
                }
                break;
            case 'timer_update':
                updateAuctionTimer(data.data.seconds);
                break;
        }
    };
    
    adminWs.onerror = (error) => {
        console.error('Admin WebSocket error:', error);
    };
    
    adminWs.onclose = () => {
        console.log('Admin WebSocket disconnected, reconnecting...');
        setTimeout(connectAdminWebSocket, 3000);
    };
}

/* ============================================================
    INITIALIZE ON PAGE LOAD - CONSOLIDATED
============================================================ */
document.addEventListener('DOMContentLoaded', function() {
    console.log('=== DOM READY - INITIALIZING ADMIN PANEL ===');
    
    try {
        // Load all data
        console.log('Loading auction status...');
        loadAuctionStatus();
        
        console.log('Loading pending players...');
        loadPendingPlayers();
        
        console.log('Loading pending approvals...');
        loadPendingApprovals();
        
        console.log('Loading current live player...');
        loadCurrentLivePlayer();
        
        console.log('Loading players for admin...');
        loadPlayersAdmin();
        
        console.log('Loading live monitor...');
        loadLiveMonitor();
        
        console.log('Loading analytics...');
        loadAnalytics();
        
        console.log('Connecting WebSocket...');
        connectAdminWebSocket();
        
        // Setup filter listeners after a short delay
        setTimeout(() => {
            console.log('Setting up filter listeners...');
            setupFilterListeners();
        }, 200);
        
        // Setup tab event listener for Player Management
        const playerMgmtTab = document.getElementById('player-mgmt-tab');
        if (playerMgmtTab) {
            console.log('Setting up Player Management tab listener...');
            playerMgmtTab.addEventListener('shown.bs.tab', function () {
                console.log('Player Management tab shown');
                setupFilterListeners();
                renderAdminPlayerTabs();
            });
        } else {
            console.warn('Player Management tab not found!');
        }
        
        console.log('=== ADMIN PANEL INITIALIZATION COMPLETE ===');
    } catch (error) {
        console.error('=== ERROR DURING INITIALIZATION ===', error);
    }
});

// Auto-refresh live monitor every 5 seconds (reduced from 30)
setInterval(loadLiveMonitor, 5000);


/* ============================================================
    LIVE MONITORING PANEL
============================================================ */
async function loadLiveMonitor() {
    try {
        const [statusRes, statsRes] = await Promise.allSettled([
            api("/auction/status"),
            api("/admin/dashboard/stats").catch(e => ({ status: 403 }))
        ]);
        
        // Handle auction status
        let status = null;
        if (statusRes.status === 'fulfilled') {
            status = await statusRes.value.json();
        }
        
        // Handle stats (may be 403)
        let stats = null;
        if (statsRes.status === 'fulfilled' && statsRes.value?.status !== 403) {
            stats = await statsRes.value.json();
        }
        
        // Update monitor cards
        if (status) {
            document.getElementById('monitor-current-player').textContent = 
                status.current_player_name || '-';
        }
        
        if (stats) {
            document.getElementById('monitor-total-revenue').textContent = 
                '₹' + (stats.total_revenue || 0).toLocaleString();
        }
        
        // Get current player's highest bid
        if (status && status.current_player_id) {
            try {
                const bidRes = await api(`/auction/bid_history/${status.current_player_id}`);
                const bidData = await bidRes.json();
                
                if (bidData.bids && bidData.bids.length > 0) {
                    const highestBid = bidData.bids[0];
                    document.getElementById('monitor-highest-bid').textContent = 
                        '₹' + highestBid.bid_amount.toLocaleString();
                    document.getElementById('monitor-leading-team').textContent = 
                        highestBid.team_name || '-';
                } else {
                    document.getElementById('monitor-highest-bid').textContent = '₹0';
                    document.getElementById('monitor-leading-team').textContent = '-';
                }
            } catch (e) {
                // Silently handle bid history errors
                console.log('Could not load bid history for current player');
            }
        }
    } catch (error) {
        console.error('Error loading live monitor:', error);
    }
}


/* ============================================================
    ANALYTICS FUNCTIONS
============================================================ */
let revenueChart, soldUnsoldChart, roleChart, teamSpendingChart;

async function loadAnalytics() {
    try {
        // Try to fetch analytics data, but handle 403 errors gracefully
        const [statsRes, revenueRes, spendingRes] = await Promise.allSettled([
            api("/admin/dashboard/stats").catch(e => ({ status: 403 })),
            api("/admin/dashboard/revenue_by_category").catch(e => ({ status: 403 })),
            api("/admin/dashboard/team_spending").catch(e => ({ status: 403 }))
        ]);
        
        // Check if all endpoints returned 403
        const allForbidden = [statsRes, revenueRes, spendingRes].every(
            res => res.status === 'rejected' || res.value?.status === 403
        );
        
        if (allForbidden) {
            console.log('Analytics endpoints not accessible (403). Hiding analytics tab.');
            // Hide analytics tab if all endpoints are forbidden
            const analyticsTab = document.querySelector('[data-bs-target="#analytics"]');
            if (analyticsTab) {
                analyticsTab.style.display = 'none';
            }
            return;
        }
        
        // Parse successful responses
        let stats = null, revenue = null, spending = null;
        
        if (statsRes.status === 'fulfilled' && statsRes.value?.status !== 403) {
            stats = await statsRes.value.json();
        }
        if (revenueRes.status === 'fulfilled' && revenueRes.value?.status !== 403) {
            revenue = await revenueRes.value.json();
        }
        if (spendingRes.status === 'fulfilled' && spendingRes.value?.status !== 403) {
            spending = await spendingRes.value.json();
        }
        
        // Update summary stats if available
        if (stats) {
            document.getElementById('analytics-total-revenue').textContent = 
                '₹' + (stats.total_revenue || 0).toLocaleString();
            document.getElementById('analytics-total-bids').textContent = 
                stats.total_bids || 0;
        }
        
        // Find highest sold player
        try {
            const playersRes = await api("/players");
            const playersData = await playersRes.json();
            const players = playersData.players || playersData;
            const soldPlayers = players.filter(p => p.status === 'sold');
            
            if (soldPlayers.length > 0) {
                const highest = soldPlayers.reduce((max, p) => 
                    (p.final_bid || 0) > (max.final_bid || 0) ? p : max
                );
                document.getElementById('analytics-highest-player').textContent = highest.name;
                document.getElementById('analytics-highest-amount').textContent = 
                    '₹' + (highest.final_bid || 0).toLocaleString();
            }
        } catch (e) {
            console.log('Could not load player data for analytics');
        }
        
        // Find most expensive team purchase
        if (spending && spending.teams && spending.teams.length > 0) {
            const mostExpensive = spending.teams.reduce((max, t) => 
                t.total_spent > max.total_spent ? t : max
            );
            document.getElementById('analytics-expensive-team').textContent = 
                mostExpensive.team_name;
            document.getElementById('analytics-expensive-amount').textContent = 
                '₹' + mostExpensive.total_spent.toLocaleString();
        }
        
        // Render charts only if data is available
        if (revenue && revenue.categories) {
            renderRevenueChart(revenue.categories);
        }
        if (stats) {
            renderSoldUnsoldChart(stats);
            if (stats.role_stats) {
                renderRoleChart(stats.role_stats);
            }
        }
        if (spending && spending.teams) {
            renderTeamSpendingChart(spending.teams);
        }
        
    } catch (error) {
        console.error('Error loading analytics:', error);
        // Show user-friendly message
        const analyticsContent = document.getElementById('analytics');
        if (analyticsContent) {
            analyticsContent.innerHTML = `
                <div class="alert alert-warning" role="alert">
                    <i class="fas fa-exclamation-triangle"></i>
                    Analytics data is currently unavailable. Please check back later.
                </div>
            `;
        }
    }
}

function renderRevenueChart(categories) {
    const ctx = document.getElementById('revenue-chart');
    if (!ctx) return;
    
    if (revenueChart) revenueChart.destroy();
    
    revenueChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: categories.map(c => c.category),
            datasets: [{
                label: 'Revenue (₹)',
                data: categories.map(c => c.revenue),
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function renderSoldUnsoldChart(stats) {
    const ctx = document.getElementById('sold-unsold-chart');
    if (!ctx) return;
    
    if (soldUnsoldChart) soldUnsoldChart.destroy();
    
    soldUnsoldChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Sold', 'Unsold', 'Available'],
            datasets: [{
                data: [
                    stats.sold_players || 0,
                    stats.unsold_players || 0,
                    stats.available_players || 0
                ],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.6)',
                    'rgba(255, 99, 132, 0.6)',
                    'rgba(255, 206, 86, 0.6)'
                ]
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

function renderRoleChart(roleStats) {
    const ctx = document.getElementById('role-chart');
    if (!ctx) return;
    
    if (roleChart) roleChart.destroy();
    
    const roles = Object.keys(roleStats);
    
    roleChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: roles,
            datasets: [{
                data: roles.map(r => roleStats[r].total),
                backgroundColor: [
                    'rgba(255, 99, 132, 0.6)',
                    'rgba(54, 162, 235, 0.6)',
                    'rgba(255, 206, 86, 0.6)',
                    'rgba(75, 192, 192, 0.6)'
                ]
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

function renderTeamSpendingChart(teams) {
    const ctx = document.getElementById('team-spending-chart');
    if (!ctx) return;
    
    if (teamSpendingChart) teamSpendingChart.destroy();
    
    // Sort teams by spending
    teams.sort((a, b) => b.total_spent - a.total_spent);
    
    teamSpendingChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: teams.map(t => t.team_name),
            datasets: [{
                label: 'Total Spent (₹)',
                data: teams.map(t => t.total_spent),
                backgroundColor: 'rgba(153, 102, 255, 0.6)',
                borderColor: 'rgba(153, 102, 255, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            indexAxis: 'y',
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { beginAtZero: true }
            }
        }
    });
}


/* ============================================================
    ACTIVITY LOGS
============================================================ */
async function loadActivityLogs() {
    try {
        const res = await api("/admin/activity-logs?limit=100");
        
        if (!res.ok) {
            if (res.status === 403) {
                console.log('Activity logs not accessible (403)');
                const tbody = document.getElementById('activity-logs-tbody');
                if (tbody) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-warning"><i class="fas fa-lock"></i> Activity logs are not accessible</td></tr>';
                }
                return;
            }
            throw new Error(`HTTP ${res.status}`);
        }
        
        const data = await res.json();
        
        const tbody = document.getElementById('activity-logs-tbody');
        tbody.innerHTML = '';
        
        if (!data.logs || data.logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No activity logs found</td></tr>';
            return;
        }
        
        data.logs.forEach(log => {
            const tr = document.createElement('tr');
            const time = new Date(log.timestamp).toLocaleString();
            const statusBadge = log.is_winning ? 
                '<span class="badge bg-success">Winning</span>' : 
                '<span class="badge bg-secondary">Outbid</span>';
            
            tr.innerHTML = `
                <td><small>${time}</small></td>
                <td><span class="badge bg-info">${log.type}</span></td>
                <td>${log.player_name}</td>
                <td>${log.team_name}</td>
                <td>₹${log.amount.toLocaleString()}</td>
                <td>${statusBadge}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error loading activity logs:', error);
        const tbody = document.getElementById('activity-logs-tbody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger"><i class="fas fa-exclamation-triangle"></i> Error loading activity logs</td></tr>';
        }
    }
}


/* ============================================================
    BID HISTORY
============================================================ */
async function loadBidHistory() {
    try {
        const res = await api("/auction/bid_history");
        
        if (!res.ok) {
            if (res.status === 403) {
                console.log('Bid history not accessible (403)');
                const tbody = document.getElementById('bid-history-tbody');
                if (tbody) {
                    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-warning"><i class="fas fa-lock"></i> Bid history is not accessible</td></tr>';
                }
                return;
            }
            console.error('Failed to load bid history:', res.status);
            const tbody = document.getElementById('bid-history-tbody');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No bid history available</td></tr>';
            }
            return;
        }
        
        const data = await res.json();
        
        const tbody = document.getElementById('bid-history-tbody');
        if (!tbody) {
            console.error('bid-history-tbody element not found');
            return;
        }
        
        tbody.innerHTML = '';
        
        if (!data.bids || data.bids.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No bid history found</td></tr>';
            return;
        }
        
        data.bids.forEach(bid => {
            const tr = document.createElement('tr');
            const time = new Date(bid.timestamp).toLocaleString();
            const winningBadge = bid.is_winning ? 
                '<span class="badge bg-success">✓</span>' : 
                '<span class="badge bg-secondary">-</span>';
            
            tr.innerHTML = `
                <td><small>${time}</small></td>
                <td>${bid.player_name || '-'}</td>
                <td>${bid.team_name || '-'}</td>
                <td>₹${bid.bid_amount.toLocaleString()}</td>
                <td>${winningBadge}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error loading bid history:', error);
        const tbody = document.getElementById('bid-history-tbody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error loading bid history</td></tr>';
        }
    }
}


/* ============================================================
    EXPORT FUNCTIONS
============================================================ */
async function exportAuctionResults() {
    try {
        const res = await api("/players");
        const data = await res.json();
        const players = data.players || data;
        
        const soldPlayers = players.filter(p => p.status === 'sold');
        
        if (soldPlayers.length === 0) {
            alert('No sold players to export');
            return;
        }
        
        // Create CSV
        let csv = 'Player Name,Role,Category,Base Price,Final Bid,Team,Auction Round\n';
        
        soldPlayers.forEach(p => {
            const teamRes = p.final_team ? 
                (async () => {
                    const t = await api(`/teams/${p.final_team}`);
                    return await t.json();
                })() : null;
            
            csv += `"${p.name}","${p.role || '-'}","${p.category || '-'}",${p.base_price || 0},${p.final_bid || 0},"${p.final_team || '-'}",${p.auction_round || 1}\n`;
        });
        
        // Download
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `auction_results_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        
        alert('Auction results exported successfully!');
    } catch (error) {
        console.error('Error exporting auction results:', error);
        alert('Error exporting auction results');
    }
}

async function exportTeamSummary() {
    try {
        const res = await api("/teams/");
        const teams = await res.json();
        
        if (teams.length === 0) {
            alert('No teams to export');
            return;
        }
        
        // Create CSV
        let csv = 'Team Name,Budget,Total Spent,Remaining Budget,Players Count\n';
        
        teams.forEach(t => {
            csv += `"${t.name}",${t.budget},${t.total_spent},${t.remaining_budget},${t.players_count}\n`;
        });
        
        // Download
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `team_summary_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        
        alert('Team summary exported successfully!');
    } catch (error) {
        console.error('Error exporting team summary:', error);
        alert('Error exporting team summary');
    }
}

async function changeAdminPassword() {
    const currentPassword = prompt('Enter current password:');
    if (!currentPassword) return;
    
    const newPassword = prompt('Enter new password (min 8 characters):');
    if (!newPassword || newPassword.length < 8) {
        alert('Password must be at least 8 characters');
        return;
    }
    
    const confirmPassword = prompt('Confirm new password:');
    if (newPassword !== confirmPassword) {
        alert('Passwords do not match');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('current_password', currentPassword);
        formData.append('new_password', newPassword);
        
        const res = await api('/admin/change-password', {
            method: 'POST',
            body: formData
        });
        
        const data = await res.json();
        
        if (res.ok && data.ok) {
            alert('Password changed successfully! Please login again.');
            logout();
        } else {
            alert(data.detail || 'Failed to change password');
        }
    } catch (error) {
        console.error('Error changing password:', error);
        alert('Error changing password');
    }
}


/* ============================================================
    RE-AUCTION CONTROLS
============================================================ */
document.getElementById("btn-start-reauction").addEventListener("click", async () => {
    if (!confirm("Start re-auction for all unsold players?")) return;
    
    const res = await api("/auction/start-reauction", { method: "POST" });
    const data = await res.json();
    
    const statusEl = document.getElementById("reauction-status");
    statusEl.classList.remove("d-none");
    
    if (res.ok && data.ok) {
        statusEl.className = "card-footer alert alert-success mb-0";
        statusEl.textContent = `${data.message} - ${data.unsold_players_count} players moved to round ${data.round}`;
    } else {
        statusEl.className = "card-footer alert alert-danger mb-0";
        statusEl.textContent = data.detail || "Failed to start re-auction";
    }
    
    loadAuctionStatus();
    loadPlayersAdmin();
});

document.getElementById("btn-view-unsold").addEventListener("click", async () => {
    const res = await api("/auction/unsold-players");
    const data = await res.json();
    
    const section = document.getElementById("unsold-section");
    const list = document.getElementById("unsold-players-list");
    
    section.classList.remove("d-none");
    list.innerHTML = "";
    
    if (!data.unsold_players || data.unsold_players.length === 0) {
        list.innerHTML = '<div class="col-12 text-center text-muted">No unsold players found</div>';
        return;
    }
    
    data.unsold_players.forEach(p => {
        const col = document.createElement("div");
        col.className = "col-md-4 col-lg-3 mb-3";
        
        const imageHtml = p.image_path ? 
            `<img src="${p.image_path}" class="img-fluid rounded mb-2" style="max-height:150px;object-fit:cover;" alt="${p.name}" onerror="this.onerror=null; this.outerHTML='<div class=\\'bg-secondary text-white rounded d-flex align-items-center justify-content-center mb-2\\' style=\\'height:150px;font-size:48px;\\'>${p.name.charAt(0).toUpperCase()}</div>';">` :
            `<div class="bg-secondary text-white rounded d-flex align-items-center justify-content-center mb-2" style="height:150px;font-size:48px;">${p.name.charAt(0).toUpperCase()}</div>`;
        
        col.innerHTML = `
            <div class="card h-100">
                <div class="card-body text-center">
                    ${imageHtml}
                    <h6 class="card-title">${p.name}</h6>
                    <p class="card-text small">
                        ${p.role ? `<span class="badge bg-primary">${p.role}</span>` : ''}
                        ${p.category ? `<span class="badge bg-secondary">${p.category}</span>` : ''}
                        <br>
                        <strong>Base Price:</strong> ₹${p.base_price || 0}<br>
                        <strong>Round:</strong> ${p.auction_round || 1}
                    </p>
                </div>
            </div>
        `;
        
        list.appendChild(col);
    });
});

function closeUnsoldSection() {
    document.getElementById("unsold-section").classList.add("d-none");
}


/* ============================================================
    ADMIN FILTER CONTROLS - Moved to setupFilterListeners()
============================================================ */
// Filter setup moved to DOMContentLoaded initialization


/* ============================================================
    TAB CHANGE LISTENERS
============================================================ */
document.getElementById('analytics-tab')?.addEventListener('shown.bs.tab', function () {
    loadAnalytics();
});

document.getElementById('logs-tab')?.addEventListener('shown.bs.tab', function () {
    loadActivityLogs();
    loadBidHistory();
});


/* ============================================================
    ENHANCED TEAM MANAGEMENT - Removed (now in admin_teams.js)
============================================================ */
// All enhanced team management functions moved to admin_teams.js




/* ============================================================
    ADMIN FILTER CONTROLS
============================================================ */
function setupFilterListeners() {
    const adminSearchName = document.getElementById('admin-search-name');
    const adminFilterRole = document.getElementById('admin-filter-role');
    const adminFilterCategory = document.getElementById('admin-filter-category');
    const adminFilterStatus = document.getElementById('admin-filter-status');
    const adminApplyFiltersBtn = document.getElementById('admin-btn-apply-filters');

    console.log('Setting up filters...', {
        searchName: !!adminSearchName,
        filterRole: !!adminFilterRole,
        filterCategory: !!adminFilterCategory,
        filterStatus: !!adminFilterStatus,
        applyBtn: !!adminApplyFiltersBtn
    });

    if (adminSearchName) {
        // Remove old listener if exists
        adminSearchName.replaceWith(adminSearchName.cloneNode(true));
        const newSearchName = document.getElementById('admin-search-name');
        newSearchName.addEventListener('input', () => {
            console.log('Search filter triggered:', newSearchName.value);
            renderAdminPlayerTabs();
        });
    }

    if (adminFilterRole) {
        adminFilterRole.replaceWith(adminFilterRole.cloneNode(true));
        const newFilterRole = document.getElementById('admin-filter-role');
        newFilterRole.addEventListener('change', () => {
            console.log('Role filter triggered:', newFilterRole.value);
            renderAdminPlayerTabs();
        });
    }

    if (adminFilterCategory) {
        adminFilterCategory.replaceWith(adminFilterCategory.cloneNode(true));
        const newFilterCategory = document.getElementById('admin-filter-category');
        newFilterCategory.addEventListener('change', () => {
            console.log('Category filter triggered:', newFilterCategory.value);
            renderAdminPlayerTabs();
        });
    }

    if (adminFilterStatus) {
        adminFilterStatus.replaceWith(adminFilterStatus.cloneNode(true));
        const newFilterStatus = document.getElementById('admin-filter-status');
        newFilterStatus.addEventListener('change', () => {
            console.log('Status filter triggered:', newFilterStatus.value);
            renderAdminPlayerTabs();
        });
    }

    if (adminApplyFiltersBtn) {
        adminApplyFiltersBtn.replaceWith(adminApplyFiltersBtn.cloneNode(true));
        const newApplyBtn = document.getElementById('admin-btn-apply-filters');
        newApplyBtn.addEventListener('click', () => {
            console.log('Apply filters button clicked');
            renderAdminPlayerTabs();
        });
    }
}


/* ============================================================
    DEBOUNCED FILTER FOR SEARCH INPUT
============================================================ */
let adminFilterTimeout = null;
function debouncedAdminFilter() {
    clearTimeout(adminFilterTimeout);
    adminFilterTimeout = setTimeout(() => {
        renderAdminPlayerTabs();
    }, 300); // Wait 300ms after user stops typing
}


/* ============================================================
    DELETE PLAYER
============================================================ */
async function deletePlayer(playerId, playerName) {
    // Confirm deletion
    const confirmed = confirm(`Are you sure you want to delete player "${playerName}"?\n\nThis action cannot be undone!`);
    
    if (!confirmed) {
        return;
    }
    
    try {
        console.log('Deleting player:', playerId, playerName);
        
        const response = await api(`/players/delete/${playerId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete player');
        }
        
        const result = await response.json();
        alert(`✅ Player "${playerName}" deleted successfully`);
        
        // Reload players
        loadPlayersAdmin();
        
    } catch (error) {
        console.error('Error deleting player:', error);
        alert(`❌ Failed to delete player: ${error.message}`);
    }
}

// Expose deletePlayer globally
window.deletePlayer = deletePlayer;


/* ============================================================
    AUCTION TIMER DISPLAY & SOUND EFFECTS
============================================================ */
let lastBeepSecond = -1;

function updateAuctionTimer(seconds) {
    console.log('Admin timer update:', seconds);
    const timerCard = document.getElementById('auction-timer-card');
    const timerDisplay = document.getElementById('auction-timer-display');
    const progressBar = document.getElementById('timer-progress-bar');
    
    console.log('Timer elements:', {
        timerCard: !!timerCard,
        timerDisplay: !!timerDisplay,
        progressBar: !!progressBar
    });
    
    if (!timerCard || !timerDisplay || !progressBar) {
        console.error('Timer elements not found!');
        return;
    }
    
    // Show timer card when auction is active
    if (seconds > 0) {
        console.log('Showing timer with', seconds, 'seconds');
        timerCard.style.display = 'block';
        
        // Format time as MM:SS
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        timerDisplay.textContent = `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        
        // Update progress bar - use 30 as max
        const percentage = Math.min(100, (seconds / 30) * 100);
        progressBar.style.width = percentage + '%';
        
        // Change color based on time remaining
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
        
        // Play countdown beeps
        if (seconds <= 10 && seconds !== lastBeepSecond) {
            playCountdownBeep(seconds);
            lastBeepSecond = seconds;
        }
    } else {
        // Hide timer when not active
        timerCard.style.display = 'none';
        lastBeepSecond = -1;
    }
}

function playCountdownBeep(seconds) {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        // Different frequencies for different countdown stages
        if (seconds <= 3) {
            oscillator.frequency.value = 1200; // High pitch for final countdown
            gainNode.gain.value = 0.3;
        } else if (seconds <= 5) {
            oscillator.frequency.value = 900; // Medium-high pitch
            gainNode.gain.value = 0.2;
        } else {
            oscillator.frequency.value = 600; // Lower pitch
            gainNode.gain.value = 0.15;
        }
        
        oscillator.type = 'sine';
        oscillator.start();
        oscillator.stop(audioContext.currentTime + 0.1);
    } catch (error) {
        console.log('Audio not supported');
    }
}

// Add CSS animation for pulse effect
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
`;
document.head.appendChild(style);


/* ============================================================
    EXPORT FUNCTIONALITY
============================================================ */
async function exportBidHistory() {
    try {
        const response = await api("/auction/bid_history");
        const data = await response.json();
        
        if (!data.bids || data.bids.length === 0) {
            alert('No bid history to export');
            return;
        }
        
        // Create CSV content
        let csv = 'Timestamp,Player Name,Team Name,Bid Amount,Is Winning\n';
        
        data.bids.forEach(bid => {
            const timestamp = new Date(bid.timestamp).toLocaleString();
            const playerName = (bid.player_name || 'Unknown').replace(/,/g, ';');
            const teamName = (bid.team_name || 'Unknown').replace(/,/g, ';');
            const bidAmount = bid.bid_amount || 0;
            const isWinning = bid.is_winning ? 'Yes' : 'No';
            
            csv += `"${timestamp}","${playerName}","${teamName}",${bidAmount},${isWinning}\n`;
        });
        
        // Create download link
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        
        link.setAttribute('href', url);
        link.setAttribute('download', `bid_history_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        alert('Bid history exported successfully!');
    } catch (error) {
        console.error('Export error:', error);
        alert('Failed to export bid history');
    }
}

async function exportPlayerRoster() {
    try {
        const response = await api("/players?include_unapproved=false");
        const data = await response.json();
        const players = data.players || data;
        
        if (!players || players.length === 0) {
            alert('No players to export');
            return;
        }
        
        // Create CSV content
        let csv = 'Name,Role,Category,Base Price,Status,Final Bid,Team Name\n';
        
        players.forEach(player => {
            const name = (player.name || 'Unknown').replace(/,/g, ';');
            const role = (player.role || 'N/A').replace(/,/g, ';');
            const category = (player.category || 'N/A').replace(/,/g, ';');
            const basePrice = player.base_price || 0;
            const status = player.status || 'available';
            const finalBid = player.final_bid || 0;
            const teamName = (player.team_name || 'N/A').replace(/,/g, ';');
            
            csv += `"${name}","${role}","${category}",${basePrice},"${status}",${finalBid},"${teamName}"\n`;
        });
        
        // Create download link
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        
        link.setAttribute('href', url);
        link.setAttribute('download', `player_roster_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        alert('Player roster exported successfully!');
    } catch (error) {
        console.error('Export error:', error);
        alert('Failed to export player roster');
    }
}


/* ============================================================
    UNDO LAST SOLD PLAYER
============================================================ */
async function undoLastSold() {
    try {
        // First, get info about the last sold player
        const infoRes = await api('/admin/auction/last-sold-info');
        const infoData = await infoRes.json();
        
        if (!infoData.ok || !infoData.player) {
            alert('No sold players found to undo');
            return;
        }
        
        const player = infoData.player;
        
        // Confirm with admin
        const confirmMsg = `Are you sure you want to UNDO this sale?\n\n` +
            `Player: ${player.name}\n` +
            `Team: ${player.team_name}\n` +
            `Amount: ₹${player.final_bid.toLocaleString()}\n\n` +
            `This will:\n` +
            `✓ Restore ${player.name} to auction\n` +
            `✓ Refund ₹${player.final_bid.toLocaleString()} to ${player.team_name}\n` +
            `✓ Remove player from team's roster\n\n` +
            `This action will be logged.`;
        
        if (!confirm(confirmMsg)) {
            return;
        }
        
        // Perform undo
        const undoRes = await api('/admin/auction/undo-last-sold', {
            method: 'POST'
        });
        
        const undoData = await undoRes.json();
        
        if (undoData.ok) {
            alert(`✅ ${undoData.message}`);
            
            // Reload relevant data
            loadPlayersAdmin();
            if (typeof loadTeams === 'function') {
                loadTeams();
            }
            loadLiveMonitor();
            loadAnalytics();
        } else {
            alert(`❌ Failed to undo: ${undoData.detail || 'Unknown error'}`);
        }
        
    } catch (error) {
        console.error('Error undoing last sold:', error);
        alert('❌ Error undoing last sold player. Please try again.');
    }
}

// Expose function globally
window.undoLastSold = undoLastSold;


/* ============================================================
    RESET AUCTION FEATURE
    Version: 8.0.0
============================================================ */
async function resetAuction() {
    try {
        // Get preview of what will be reset
        const previewRes = await api('/admin/auction/reset-preview');
        const previewData = await previewRes.json();
        
        if (!previewData.ok) {
            alert('Failed to get reset preview');
            return;
        }
        
        const preview = previewData.preview;
        
        // Confirm with admin - show detailed preview
        const confirmMsg = `⚠️ RESET ENTIRE AUCTION ⚠️\n\n` +
            `This will reset EVERYTHING:\n\n` +
            `📊 Players:\n` +
            `  • ${preview.sold_players} sold players → available\n` +
            `  • ${preview.unsold_players} unsold players → available\n` +
            `  • ${preview.in_auction_players} in-auction players → available\n` +
            `  • Total: ${preview.players_to_reset} players reset\n\n` +
            `💰 Teams:\n` +
            `  • ${preview.teams_to_reset} teams reset to original budgets\n` +
            `  • All rosters cleared\n\n` +
            `📝 Data:\n` +
            `  • ${preview.bids_to_clear} bids will be deleted\n` +
            `  • Auction round reset to 1\n\n` +
            `⚠️ THIS CANNOT BE UNDONE!\n\n` +
            `Type "RESET" to confirm:`;
        
        const userInput = prompt(confirmMsg);
        
        if (userInput !== 'RESET') {
            alert('Reset cancelled');
            return;
        }
        
        // Show loading indicator
        const resetBtn = document.getElementById('btn-reset-auction');
        if (resetBtn) {
            resetBtn.disabled = true;
            resetBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Resetting...';
        }
        
        // Perform reset
        const resetRes = await api('/admin/auction/reset', {
            method: 'POST'
        });
        
        const resetData = await resetRes.json();
        
        if (resetData.ok) {
            alert(`✅ Auction Reset Complete!\n\n` +
                `Players reset: ${resetData.details.players_reset}\n` +
                `Bids cleared: ${resetData.details.bids_cleared}\n` +
                `Teams reset: ${resetData.details.teams_reset}\n\n` +
                `The auction is now ready to start fresh!`);
            
            // Reload all data
            loadAuctionStatus();
            loadPlayersAdmin();
            if (typeof loadTeams === 'function') {
                loadTeams();
            }
            loadLiveMonitor();
            loadAnalytics();
            loadCurrentLivePlayer();
        } else {
            alert(`❌ Reset failed: ${resetData.detail || 'Unknown error'}`);
        }
        
    } catch (error) {
        console.error('Error resetting auction:', error);
        alert('❌ Error resetting auction. Please try again.');
    } finally {
        // Re-enable button
        const resetBtn = document.getElementById('btn-reset-auction');
        if (resetBtn) {
            resetBtn.disabled = false;
            resetBtn.innerHTML = '<i class="fas fa-redo"></i> Reset Entire Auction';
        }
    }
}

// Expose function globally
window.resetAuction = resetAuction;


/* ============================================================
    NOTIFICATION SYSTEM
    Version: 8.0.0
============================================================ */
let notificationPermission = 'default';

// Request notification permission
async function requestNotificationPermission() {
    if (!('Notification' in window)) {
        console.log('Browser does not support notifications');
        return false;
    }
    
    if (Notification.permission === 'granted') {
        notificationPermission = 'granted';
        return true;
    }
    
    if (Notification.permission !== 'denied') {
        const permission = await Notification.requestPermission();
        notificationPermission = permission;
        return permission === 'granted';
    }
    
    return false;
}

// Show browser notification
function showNotification(title, options = {}) {
    if (notificationPermission !== 'granted') {
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
        
        // Auto-close after 5 seconds
        setTimeout(() => notification.close(), 5000);
        
        // Handle click
        notification.onclick = function(event) {
            event.preventDefault();
            window.focus();
            notification.close();
        };
    } catch (error) {
        console.error('Error showing notification:', error);
    }
}

// Initialize notifications on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(() => {
            requestNotificationPermission();
        }, 2000);
    });
} else {
    setTimeout(() => {
        requestNotificationPermission();
    }, 2000);
}
