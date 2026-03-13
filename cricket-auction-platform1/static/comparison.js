/**
 * Team Comparison System
 * Version: 1.0.0
 */

let comparisonData = null;

// Initialize comparison
async function initComparison() {
    await loadMyTeamAnalysis();
}

// Load my team analysis
async function loadMyTeamAnalysis() {
    try {
        const res = await api('/comparison/my-team-analysis');
        const data = await res.json();
        
        if (data.ok) {
            renderTeamAnalysis(data.analysis);
        }
    } catch (error) {
        console.error('Error loading team analysis:', error);
    }
}

// Render team analysis
function renderTeamAnalysis(analysis) {
    const container = document.getElementById('team-analysis-container');
    if (!container) return;
    
    container.innerHTML = `
        <div class="analysis-section">
            <h4>${analysis.team_name} - Squad Analysis</h4>
            
            <div class="analysis-stats">
                <div class="analysis-stat">
                    <div class="stat-label">Total Players</div>
                    <div class="stat-value">${analysis.total_players}</div>
                </div>
                <div class="analysis-stat">
                    <div class="stat-label">Total Spent</div>
                    <div class="stat-value">₹${analysis.total_spent.toLocaleString()}</div>
                </div>
                <div class="analysis-stat">
                    <div class="stat-label">Remaining Budget</div>
                    <div class="stat-value">₹${analysis.remaining_budget.toLocaleString()}</div>
                </div>
            </div>
            
            ${analysis.strengths.length > 0 ? `
                <div class="analysis-strengths">
                    <h5><i class="bi bi-check-circle-fill text-success"></i> Strengths</h5>
                    <ul>
                        ${analysis.strengths.map(s => `<li>${s}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            
            ${analysis.weaknesses.length > 0 ? `
                <div class="analysis-weaknesses">
                    <h5><i class="bi bi-exclamation-triangle-fill text-warning"></i> Weaknesses</h5>
                    <ul>
                        ${analysis.weaknesses.map(w => `<li>${w}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            
            ${analysis.recommendations.length > 0 ? `
                <div class="analysis-recommendations">
                    <h5><i class="bi bi-lightbulb-fill text-info"></i> Recommendations</h5>
                    <ul>
                        ${analysis.recommendations.map(r => `<li>${r}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        </div>
    `;
}

// Compare teams
async function compareTeams() {
    try {
        // Get all teams
        const teamsRes = await api('/teams/');
        const teams = await teamsRes.json();
        
        if (teams.length < 2) {
            alert('Need at least 2 teams to compare');
            return;
        }
        
        // Show team selection modal
        const selectedTeams = await showTeamSelectionModal(teams);
        if (!selectedTeams || selectedTeams.length < 2) return;
        
        // Fetch comparison data
        const teamIds = selectedTeams.join(',');
        const res = await api(`/comparison/teams?team_ids=${teamIds}`);
        const data = await res.json();
        
        if (data.ok) {
            comparisonData = data.teams;
            renderTeamComparison();
        }
    } catch (error) {
        console.error('Error comparing teams:', error);
        alert('Error comparing teams');
    }
}

// Show team selection modal
function showTeamSelectionModal(teams) {
    return new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'comparison-modal';
        modal.innerHTML = `
            <div class="comparison-modal-content">
                <h3>Select Teams to Compare</h3>
                <p>Choose 2-4 teams (hold Ctrl/Cmd for multiple)</p>
                <select id="team-select" multiple size="6" class="form-control">
                    ${teams.map(t => `<option value="${t._id}">${t.name}</option>`).join('')}
                </select>
                <div class="mt-3">
                    <button class="btn btn-primary" onclick="confirmTeamSelection()">Compare</button>
                    <button class="btn btn-secondary" onclick="closeComparisonModal()">Cancel</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        window.confirmTeamSelection = () => {
            const select = document.getElementById('team-select');
            const selected = Array.from(select.selectedOptions).map(opt => opt.value);
            modal.remove();
            resolve(selected);
        };
        
        window.closeComparisonModal = () => {
            modal.remove();
            resolve(null);
        };
    });
}

// Render team comparison
function renderTeamComparison() {
    const container = document.getElementById('comparison-results-container');
    if (!container || !comparisonData) return;
    
    container.innerHTML = `
        <div class="comparison-header">
            <h4>Team Comparison</h4>
            <button class="btn btn-sm btn-secondary" onclick="closeComparison()">Close</button>
        </div>
        
        <div class="comparison-grid">
            ${comparisonData.map(team => `
                <div class="comparison-team-card">
                    <h5>${team.team_name}</h5>
                    
                    <div class="comparison-stat">
                        <span>Players:</span>
                        <strong>${team.players_count}</strong>
                    </div>
                    
                    <div class="comparison-stat">
                        <span>Total Spent:</span>
                        <strong>₹${team.total_spent.toLocaleString()}</strong>
                    </div>
                    
                    <div class="comparison-stat">
                        <span>Budget Used:</span>
                        <strong>${team.budget_used_percent.toFixed(1)}%</strong>
                    </div>
                    
                    <div class="comparison-stat">
                        <span>Avg Price:</span>
                        <strong>₹${team.average_price.toLocaleString()}</strong>
                    </div>
                    
                    <div class="comparison-stat">
                        <span>Squad Balance:</span>
                        <strong>${team.squad_balance_score}/100</strong>
                    </div>
                    
                    <div class="comparison-stat">
                        <span>Value Score:</span>
                        <strong>${team.value_for_money_score}/100</strong>
                    </div>
                    
                    ${team.most_expensive_player ? `
                        <div class="comparison-highlight">
                            <small>Most Expensive:</small>
                            <div>${team.most_expensive_player.name}</div>
                            <div>₹${team.most_expensive_player.price.toLocaleString()}</div>
                        </div>
                    ` : ''}
                    
                    <div class="comparison-roles">
                        <small>Role Distribution:</small>
                        ${Object.entries(team.role_distribution).map(([role, count]) => `
                            <div class="role-badge">${role}: ${count}</div>
                        `).join('')}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    // Show container
    container.style.display = 'block';
}

// Close comparison
function closeComparison() {
    const container = document.getElementById('comparison-results-container');
    if (container) {
        container.style.display = 'none';
    }
}

// Expose functions globally
window.initComparison = initComparison;
window.compareTeams = compareTeams;
window.closeComparison = closeComparison;
