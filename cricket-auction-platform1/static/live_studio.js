// Hollywood Cinematic Auction Studio - Level 3
console.log('🎬 Hollywood Cinematic Studio Initializing...');

// State Management
const state = {
    soundEnabled: true,
    commentaryEnabled: false,
    players: [],
    teams: [],
    events: [],
    currentPlayer: null,
    auctionActive: false,
    stats: {},
    charts: {},
    commentary: []
};

// Configuration
const CONFIG = {
    WS_URL: `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/auction/ws`,
    POLL_INTERVAL: 3000, // Reduced from 5000 to 3000ms (3 seconds)
    MAX_EVENTS: 30,
    ANIMATION_DURATION: 500
};

// WebSocket & Timers
let ws = null;
let pollTimer = null;
let countdownTimer = null;
let commentaryTimer = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Starting Hollywood Studio');
    initializeStudio();
    initializeParticles();
});

function initializeStudio() {
    setupControlButtons();
    setupFilters();
    connectWebSocket();
    loadInitialData();
    startPolling();
}

// Particle Background
function initializeParticles() {
    const canvas = document.getElementById('particles');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    const particles = [];
    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
        particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            radius: Math.random() * 2 + 1,
            vx: (Math.random() - 0.5) * 0.5,
            vy: (Math.random() - 0.5) * 0.5
        });
    }
    
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = 'rgba(255, 215, 0, 0.3)';
        
        particles.forEach(p => {
            p.x += p.vx;
            p.y += p.vy;
            
            if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
            if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
            
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fill();
        });
        
        requestAnimationFrame(animate);
    }
    
    animate();
    
    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
}

// Control Buttons
function setupControlButtons() {
    const soundBtn = document.getElementById('soundToggle');
    const commentaryBtn = document.getElementById('commentaryToggle');
    const fullscreenBtn = document.getElementById('fullscreenToggle');
    const exportBtn = document.getElementById('exportBtn');

    if (soundBtn) soundBtn.addEventListener('click', toggleSound);
    if (commentaryBtn) commentaryBtn.addEventListener('click', toggleCommentary);
    if (fullscreenBtn) fullscreenBtn.addEventListener('click', toggleFullscreen);
    if (exportBtn) exportBtn.addEventListener('click', exportSummary);
}

function toggleSound() {
    state.soundEnabled = !state.soundEnabled;
    const btn = document.getElementById('soundToggle');
    if (btn) {
        btn.innerHTML = state.soundEnabled ? '<i class="fas fa-volume-up"></i>' : '<i class="fas fa-volume-mute"></i>';
        btn.classList.toggle('active');
    }
    showToast(state.soundEnabled ? '🔊 Sound Enabled' : '🔇 Sound Muted', 'info');
}

function toggleCommentary() {
    state.commentaryEnabled = !state.commentaryEnabled;
    const btn = document.getElementById('commentaryToggle');
    const card = document.getElementById('commentaryCard');
    if (btn) {
        btn.classList.toggle('active');
    }
    if (card) {
        card.style.display = state.commentaryEnabled ? 'block' : 'none';
    }
    showToast(state.commentaryEnabled ? '🎙️ AI Commentary ON' : '🎙️ AI Commentary OFF', 'info');
    
    if (state.commentaryEnabled) {
        startCommentary();
    } else {
        stopCommentary();
    }
}

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
    } else {
        document.exitFullscreen();
    }
}

function exportSummary() {
    const csv = generateCSV();
    downloadCSV(csv, 'auction_summary.csv');
    showToast('📥 Summary Exported', 'success');
}

function generateCSV() {
    let csv = 'Player Name,Role,Category,Status,Base Price,Final Bid,Team\n';
    state.players.forEach(p => {
        csv += `${p.name},${p.role || 'N/A'},${p.category || 'N/A'},${p.status},${p.base_price || 0},${p.final_bid || 0},${p.team_name || 'N/A'}\n`;
    });
    return csv;
}

function downloadCSV(csv, filename) {
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
}

// AI Commentary System
function startCommentary() {
    if (commentaryTimer) return;
    updateCommentary();
    commentaryTimer = setInterval(updateCommentary, 8000);
}

function stopCommentary() {
    if (commentaryTimer) {
        clearInterval(commentaryTimer);
        commentaryTimer = null;
    }
}

function updateCommentary() {
    const commentaries = [
        "The tension is building in the auction room!",
        "Teams are strategizing their next move...",
        "What an exciting auction this has been!",
        "The bidding war is heating up!",
        "This could be a record-breaking sale!",
        "Teams are going all out for this player!",
        "The auction momentum is incredible!",
        "Strategic bidding at its finest!",
        "The competition is fierce today!",
        "Every bid counts in this high-stakes auction!"
    ];
    
    const text = commentaries[Math.floor(Math.random() * commentaries.length)];
    const el = document.getElementById('commentaryText');
    if (el) {
        el.textContent = text;
        el.style.animation = 'none';
        setTimeout(() => {
            el.style.animation = 'typing 2s steps(40)';
        }, 10);
    }
}

function generateDynamicCommentary(type, data) {
    if (!state.commentaryEnabled) return;
    
    let text = '';
    if (type === 'bid') {
        text = `${data.team_name} places a bid of ₹${formatNumber(data.bid_amount)}!`;
    } else if (type === 'sold') {
        text = `SOLD! ${data.player_name} goes to ${data.team_name} for ₹${formatNumber(data.final_bid)}!`;
    } else if (type === 'unsold') {
        text = `${data.player_name} remains unsold. Teams might reconsider!`;
    }
    
    const el = document.getElementById('commentaryText');
    if (el && text) {
        el.textContent = text;
        el.style.animation = 'none';
        setTimeout(() => {
            el.style.animation = 'typing 2s steps(40)';
        }, 10);
    }
}

// WebSocket Connection
function connectWebSocket() {
    try {
        ws = new WebSocket(CONFIG.WS_URL);
        
        ws.onopen = () => {
            console.log('✅ WebSocket Connected');
            updateLiveIndicator(true);
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };
        
        ws.onerror = (error) => {
            console.error('❌ WebSocket Error:', error);
        };
        
        ws.onclose = () => {
            console.log('🔌 WebSocket Disconnected. Reconnecting...');
            updateLiveIndicator(false);
            setTimeout(connectWebSocket, 3000);
        };
    } catch (error) {
        console.error('WebSocket connection failed:', error);
    }
}

function handleWebSocketMessage(data) {
    console.log('📨 WS Message:', data.type);
    
    switch (data.type) {
        case 'bid_placed':
            handleBidPlaced(data);
            break;
        case 'player_sold':
            handlePlayerSold(data);
            break;
        case 'player_unsold':
            handlePlayerUnsold(data);
            break;
        case 'player_live':
            loadCurrentPlayer();
            break;
        case 'auction_started':
            showToast('🎬 Auction Started!', 'success');
            loadAllData();
            break;
        case 'timer_update':
            updateLiveTimer(data.data.seconds);
            break;
    }
}

function handleBidPlaced(data) {
    addEvent('bid', `New bid on ${data.player_name || 'Player'}`, data.bid_amount, data.team_name);
    loadCurrentPlayer();
    loadStats();
    playSound('bid');
    showToast(`💰 New Bid: ₹${formatNumber(data.bid_amount)}`, 'info');
    generateDynamicCommentary('bid', data);
}

function handlePlayerSold(data) {
    addEvent('sold', `SOLD: ${data.player_name || 'Player'}`, data.final_bid, data.team_name);
    showSoldAnimation(data);
    playSound('sold');
    showToast(`✅ ${data.player_name} SOLD for ₹${formatNumber(data.final_bid)}!`, 'success');
    generateDynamicCommentary('sold', data);
    setTimeout(() => {
        loadStats();
        loadCurrentPlayer();
        loadPlayers();
        loadTeams();
    }, 2000);
}

function handlePlayerUnsold(data) {
    addEvent('unsold', `UNSOLD: ${data.player_name || 'Player'}`);
    showUnsoldAnimation(data);
    playSound('unsold');
    showToast(`❌ ${data.player_name} went UNSOLD`, 'error');
    generateDynamicCommentary('unsold', data);
    setTimeout(() => {
        loadStats();
        loadCurrentPlayer();
        loadPlayers();
        loadTeams();
    }, 2000);
}

// Data Loading
function loadInitialData() {
    loadAllData();
}

function startPolling() {
    pollTimer = setInterval(() => {
        loadStats();
        loadCurrentPlayer();
    }, CONFIG.POLL_INTERVAL);
}

async function loadAllData() {
    await Promise.all([
        loadStats(),
        loadCurrentPlayer(),
        loadPlayers(),
        loadTeams()
    ]);
}

async function loadStats() {
    try {
        const response = await fetch('/viewer/analytics');
        const data = await response.json();
        
        if (data.ok) {
            const statsChanged = JSON.stringify(state.stats) !== JSON.stringify(data.statistics);
            const teamsChanged = JSON.stringify(state.teams) !== JSON.stringify(data.teams_leaderboard);
            
            state.stats = data.statistics;
            state.auctionActive = data.auction_active;
            
            if (statsChanged) {
                updateStatsDisplay(data.statistics);
            }
            
            updateLiveIndicator(data.auction_active);
            
            if (teamsChanged) {
                state.teams = data.teams_leaderboard;
                updateTeams(data.teams_leaderboard);
                updateAnalyticsChart(data.teams_leaderboard);
            }
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadCurrentPlayer() {
    try {
        const response = await fetch('/viewer/current-player');
        const data = await response.json();
        
        if (data.ok && data.auction_active && data.current_player) {
            const newPlayer = data.current_player;
            const playerChanged = !state.currentPlayer || 
                                 state.currentPlayer.id !== newPlayer.id ||
                                 state.currentPlayer.current_bid !== newPlayer.current_bid ||
                                 state.currentPlayer.status !== newPlayer.status;
            
            if (playerChanged) {
                state.currentPlayer = newPlayer;
                displayCurrentPlayer(newPlayer, data.timer_seconds);
            }
        } else {
            if (state.currentPlayer !== null) {
                state.currentPlayer = null;
                displayWaitingState();
            }
        }
    } catch (error) {
        console.error('Error loading current player:', error);
        if (state.currentPlayer !== null) {
            state.currentPlayer = null;
            displayWaitingState();
        }
    }
}

async function loadPlayers() {
    try {
        const response = await fetch('/viewer/players');
        const data = await response.json();
        
        if (data.ok) {
            const newPlayers = data.players || [];
            if (JSON.stringify(newPlayers) !== JSON.stringify(state.players)) {
                state.players = newPlayers;
                renderPlayers();
            }
        }
    } catch (error) {
        console.error('Error loading players:', error);
    }
}

async function loadTeams() {
    try {
        const response = await fetch('/viewer/analytics');
        const data = await response.json();
        
        if (data.ok) {
            state.teams = data.teams_leaderboard || [];
        }
    } catch (error) {
        console.error('Error loading teams:', error);
    }
}

// Display Functions
function updateStatsDisplay(stats) {
    animateValue('statTotal', stats.total_players || 0);
    animateValue('statSold', stats.sold_players || 0);
    animateValue('statUnsold', stats.unsold_players || 0);
    
    const revenueEl = document.getElementById('statRevenue');
    if (revenueEl) {
        revenueEl.textContent = '₹' + formatNumber(stats.total_revenue || 0);
    }
}

function displayCurrentPlayer(player, timerSeconds) {
    const stage = document.getElementById('auctionStage');
    if (!stage) return;
    
    if (player.status === 'sold') {
        stage.innerHTML = `
            <div class="result-banner">
                <div class="sold-banner">✅ SOLD!</div>
                <div style="font-size: 2.5rem; margin-top: 2rem;">${player.name}</div>
                <div style="font-size: 2rem; margin-top: 1rem; color: var(--accent-gold);">₹${formatNumber(player.current_bid)}</div>
                <div style="font-size: 1.5rem; margin-top: 0.5rem; color: var(--accent-cyan);">${player.leading_team ? player.leading_team.name : ''}</div>
            </div>
        `;
        stopCountdown();
        return;
    }
    
    if (player.status === 'unsold') {
        stage.innerHTML = `
            <div class="result-banner">
                <div class="unsold-banner">❌ UNSOLD</div>
                <div style="font-size: 2.5rem; margin-top: 2rem;">${player.name}</div>
            </div>
        `;
        stopCountdown();
        return;
    }
    
    const imgPath = player.image_path || 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="320" height="320"%3E%3Crect fill="%230a0e1a" width="320" height="320"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="120" fill="%23ffd700"%3E👤%3C/text%3E%3C/svg%3E';
    
    stage.innerHTML = `
        <div class="player-spotlight">
            <div class="player-img-container">
                <div class="player-img-glow"></div>
                <img src="${imgPath}" class="player-img" alt="${player.name}">
            </div>
            <div class="player-name">${player.name}</div>
            <div class="player-badges">
                <span class="badge-custom badge-role">${player.role || 'Player'}</span>
                <span class="badge-custom badge-category">${player.category || 'N/A'}</span>
            </div>
            <div style="color: var(--text-secondary); font-size: 1.2rem; margin-bottom: 1rem;">
                Base Price: ₹${formatNumber(player.base_price || 0)}
            </div>
            <div class="bid-display">
                <div class="bid-label">Current Bid</div>
                <div class="bid-amount" id="currentBidAmount">₹${formatNumber(player.current_bid || player.base_price || 0)}</div>
            </div>
            <div class="leading-team">
                ${player.leading_team ? `🏆 ${player.leading_team.name}` : '⏳ No bids yet'}
            </div>
            <div class="countdown-container">
                <svg class="countdown-circle" viewBox="0 0 140 140">
                    <circle cx="70" cy="70" r="64" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="10"/>
                    <circle id="countdownCircle" cx="70" cy="70" r="64" fill="none" stroke="var(--accent-red)" stroke-width="10" 
                            stroke-dasharray="402" stroke-dashoffset="0" transform="rotate(-90 70 70)" 
                            style="transition: stroke-dashoffset 1s linear"/>
                    <text x="70" y="80" text-anchor="middle" class="countdown-text" id="countdownText">${timerSeconds || 30}</text>
                </svg>
            </div>
        </div>
    `;
    
    // Don't start local countdown - we'll use WebSocket timer updates
    // The timer will be updated via timer_update WebSocket messages
}

function displayWaitingState() {
    const stage = document.getElementById('auctionStage');
    if (!stage) return;
    
    stage.innerHTML = `
        <div class="waiting-state">
            <div class="waiting-icon">⏳</div>
            <h2 style="color: var(--text-secondary);">Waiting for Auction to Start</h2>
            <p style="color: var(--text-secondary); margin-top: 1rem;">The cinematic auction will appear here</p>
        </div>
    `;
    stopCountdown();
}

function showSoldAnimation(data) {
    if (state.soundEnabled) {
        confetti({
            particleCount: 150,
            spread: 80,
            origin: { y: 0.6 },
            colors: ['#00ff88', '#ffd700', '#00d4ff']
        });
    }
}

function showUnsoldAnimation(data) {
    // Fade effect handled by CSS
}

// Countdown Timer
function startCountdown(seconds) {
    stopCountdown();
    let remaining = seconds;
    const textEl = document.getElementById('countdownText');
    const circleEl = document.getElementById('countdownCircle');
    const circumference = 402;
    
    countdownTimer = setInterval(() => {
        remaining--;
        if (textEl) textEl.textContent = remaining;
        if (circleEl) {
            const offset = circumference - (remaining / seconds) * circumference;
            circleEl.style.strokeDashoffset = offset;
        }
        if (remaining <= 0) {
            stopCountdown();
        }
    }, 1000);
}

function stopCountdown() {
    if (countdownTimer) {
        clearInterval(countdownTimer);
        countdownTimer = null;
    }
}

// Synchronized Timer Update from WebSocket
function updateLiveTimer(seconds) {
    console.log('Live studio timer update:', seconds);
    const textEl = document.getElementById('countdownText');
    const circleEl = document.getElementById('countdownCircle');
    const circumference = 402;
    
    if (!textEl || !circleEl) {
        console.log('Timer elements not found in live studio');
        return;
    }
    
    if (seconds > 0) {
        // Update display
        textEl.textContent = seconds;
        
        // Update progress circle - use 30 as max
        const percentage = Math.min(100, (seconds / 30) * 100);
        const offset = circumference - (percentage / 100) * circumference;
        circleEl.style.strokeDashoffset = offset;
        
        // Change color based on time remaining
        if (seconds <= 5) {
            circleEl.style.stroke = 'var(--accent-red)';
        } else if (seconds <= 10) {
            circleEl.style.stroke = '#f59e0b';
        } else {
            circleEl.style.stroke = 'var(--accent-cyan)';
        }
    } else {
        // Timer expired - hide or show 0
        textEl.textContent = '0';
        circleEl.style.strokeDashoffset = circumference;
    }
    
    // Stop local countdown timer since we're using server timer
    if (countdownTimer) {
        clearInterval(countdownTimer);
        countdownTimer = null;
    }
}

// Teams Display
function updateTeams(teams) {
    const container = document.getElementById('teamWarRoom');
    if (!container || !teams || teams.length === 0) {
        if (container) container.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">No teams data</p>';
        return;
    }
    
    container.innerHTML = teams.slice(0, 8).map((team, index) => {
        const spentPercent = team.total_spent && team.initial_budget ? 
            (team.total_spent / team.initial_budget * 100).toFixed(1) : 0;
        
        return `
            <div class="team-card">
                <div class="team-header">
                    <div>
                        <div class="team-name">${index === 0 ? '🏆 ' : ''}${team.name}</div>
                        <div style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.5rem;">
                            ${team.players_count || 0} players • ₹${formatNumber(team.remaining_purse || 0)} left
                        </div>
                    </div>
                    <div class="team-spent">₹${formatNumber(team.total_spent || 0)}</div>
                </div>
                <div class="budget-bar">
                    <div class="budget-fill" style="width: ${spentPercent}%"></div>
                </div>
            </div>
        `;
    }).join('');
}

// Charts
function updateAnalyticsChart(teams) {
    const canvas = document.getElementById('analyticsChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    if (state.charts.analytics) {
        state.charts.analytics.destroy();
    }
    
    const topTeams = teams.slice(0, 8);
    
    state.charts.analytics = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: topTeams.map(t => t.name),
            datasets: [{
                label: 'Total Spent',
                data: topTeams.map(t => t.total_spent || 0),
                backgroundColor: 'rgba(255, 215, 0, 0.7)',
                borderColor: 'rgba(255, 215, 0, 1)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return '₹' + formatNumber(context.parsed.y);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.8)',
                        callback: function(value) {
                            return '₹' + (value / 1000).toFixed(0) + 'k';
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    }
                },
                x: {
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.8)',
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Event Feed
function addEvent(type, text, amount = null, team = null) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    const event = {
        type: type,
        text: text,
        amount: amount,
        team: team,
        time: timeStr,
        timestamp: now.getTime()
    };
    
    state.events.unshift(event);
    
    if (state.events.length > CONFIG.MAX_EVENTS) {
        state.events = state.events.slice(0, CONFIG.MAX_EVENTS);
    }
    
    renderEvents();
}

function renderEvents() {
    const container = document.getElementById('eventFeed');
    if (!container) return;
    
    if (state.events.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">Waiting for events...</p>';
        return;
    }
    
    container.innerHTML = state.events.map(e => {
        let icon = '📢';
        if (e.type === 'bid') icon = '💰';
        else if (e.type === 'sold') icon = '✅';
        else if (e.type === 'unsold') icon = '❌';
        
        const amountHtml = e.amount ? `<div class="event-amount">₹${formatNumber(e.amount)}</div>` : '';
        const teamHtml = e.team ? `<div style="color: var(--accent-cyan); font-size: 1rem; margin-top: 0.5rem;">${e.team}</div>` : '';
        
        return `
            <div class="event-item ${e.type}">
                <div class="event-header">
                    <div class="event-text">${icon} ${e.text}</div>
                    <div class="event-time">${e.time}</div>
                </div>
                ${amountHtml}
                ${teamHtml}
            </div>
        `;
    }).join('');
}

// Player Browser
function setupFilters() {
    const searchInput = document.getElementById('playerSearch');
    const roleFilter = document.getElementById('roleFilter');
    const statusFilter = document.getElementById('statusFilter');
    
    if (searchInput) {
        let debounceTimer;
        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(renderPlayers, 300);
        });
    }
    
    if (roleFilter) roleFilter.addEventListener('change', renderPlayers);
    if (statusFilter) statusFilter.addEventListener('change', renderPlayers);
}

function renderPlayers() {
    const container = document.getElementById('playerGrid');
    if (!container) return;
    
    const searchTerm = document.getElementById('playerSearch')?.value.toLowerCase() || '';
    const roleFilter = document.getElementById('roleFilter')?.value.toLowerCase() || '';
    const statusFilter = document.getElementById('statusFilter')?.value.toLowerCase() || '';
    
    let filtered = state.players.filter(p => {
        const matchSearch = !searchTerm || (p.name && p.name.toLowerCase().includes(searchTerm));
        const matchRole = !roleFilter || (p.role && p.role.toLowerCase().includes(roleFilter));
        const matchStatus = !statusFilter || (p.status && p.status.toLowerCase() === statusFilter);
        return matchSearch && matchRole && matchStatus;
    });
    
    if (filtered.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; grid-column: 1/-1;">No players found</p>';
        return;
    }
    
    const defaultImg = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="120" height="120"%3E%3Crect fill="%230a0e1a" width="120" height="120"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="50" fill="%23ffd700"%3E👤%3C/text%3E%3C/svg%3E';
    
    container.innerHTML = filtered.map(p => {
        const imgPath = p.image_path || defaultImg;
        const statusClass = `status-${p.status || 'available'}`;
        const price = p.status === 'sold' ? `₹${formatNumber(p.final_bid || 0)}` : `Base: ₹${formatNumber(p.base_price || 0)}`;
        
        return `
            <div class="player-card">
                <img src="${imgPath}" class="player-card-img" alt="${p.name}">
                <div class="player-card-name">${p.name || 'Unknown'}</div>
                <div class="player-card-info">${p.role || 'N/A'} • ${p.category || 'N/A'}</div>
                <div class="player-card-info" style="margin-top: 0.8rem;">${price}</div>
                ${p.team_name ? `<div class="player-card-info" style="color: var(--accent-cyan);">${p.team_name}</div>` : ''}
                <span class="status-badge ${statusClass}">${(p.status || 'available').toUpperCase()}</span>
            </div>
        `;
    }).join('');
}

// UI Helpers
function updateLiveIndicator(isLive) {
    const indicator = document.getElementById('liveIndicator');
    if (!indicator) return;
    
    if (isLive) {
        indicator.innerHTML = '<div class="live-dot"></div><span>LIVE</span>';
    } else {
        indicator.innerHTML = '<span>OFFLINE</span>';
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    else if (type === 'error') icon = '❌';
    else if (type === 'warning') icon = '⚠️';
    
    toast.innerHTML = `<div>${icon} ${message}</div>`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.5s ease-out reverse';
        setTimeout(() => toast.remove(), 500);
    }, 3500);
}

function playSound(type) {
    if (!state.soundEnabled) return;
    
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        if (type === 'bid') {
            // Quick beep for bid
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            oscillator.frequency.value = 900;
            gainNode.gain.value = 0.12;
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.15);
            
        } else if (type === 'sold') {
            // Hammer sound effect (three quick hits)
            [0, 0.1, 0.2].forEach((delay, index) => {
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                oscillator.frequency.value = 200 - (index * 20); // Descending pitch
                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime + delay);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + delay + 0.08);
                
                oscillator.start(audioContext.currentTime + delay);
                oscillator.stop(audioContext.currentTime + delay + 0.08);
            });
            
            // Victory chime after hammer
            setTimeout(() => {
                const chime = audioContext.createOscillator();
                const chimeGain = audioContext.createGain();
                chime.connect(chimeGain);
                chimeGain.connect(audioContext.destination);
                chime.frequency.value = 1400;
                chimeGain.gain.value = 0.18;
                chime.start();
                chime.stop(audioContext.currentTime + 0.3);
            }, 300);
            
        } else if (type === 'unsold') {
            // Descending sad sound
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            oscillator.frequency.setValueAtTime(500, audioContext.currentTime);
            oscillator.frequency.exponentialRampToValueAtTime(250, audioContext.currentTime + 0.3);
            gainNode.gain.value = 0.12;
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.3);
        }
    } catch (error) {
        console.log('Audio not supported');
    }
}

function animateValue(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    
    const current = parseInt(el.textContent) || 0;
    const increment = (target - current) / 25;
    let count = 0;
    
    const timer = setInterval(() => {
        count++;
        const value = Math.floor(current + increment * count);
        el.textContent = value;
        
        if (count >= 25) {
            el.textContent = target;
            clearInterval(timer);
        }
    }, 40);
}

function formatNumber(num) {
    return new Intl.NumberFormat('en-IN').format(num);
}

// Cleanup
window.addEventListener('beforeunload', () => {
    if (ws) ws.close();
    if (pollTimer) clearInterval(pollTimer);
    if (countdownTimer) clearInterval(countdownTimer);
    if (commentaryTimer) clearInterval(commentaryTimer);
});

console.log('✅ Hollywood Cinematic Studio Ready');
