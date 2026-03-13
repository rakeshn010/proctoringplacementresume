/**
 * Team Management Module - SIMPLE WORKING VERSION
 */

let teamsData = [];
let teamModal, deleteModal;
let deleteTeamId = null;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('=== TEAM MANAGEMENT INITIALIZING ===');
    
    if (typeof window.api !== 'function') {
        console.error('API function not available!');
        setTimeout(function() {
            if (typeof window.api === 'function') {
                init();
            }
        }, 500);
        return;
    }
    
    init();
});

function init() {
    teamModal = new bootstrap.Modal(document.getElementById('teamModal'));
    deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
    loadTeams();
    console.log('=== TEAM MANAGEMENT INITIALIZED ===');
}

// Load teams
async function loadTeams() {
    try {
        const response = await window.api('/teams/');
        if (!response.ok) throw new Error('Failed to load teams');
        
        teamsData = await response.json();
        console.log('Teams loaded:', teamsData.length);
        renderTeams();
    } catch (error) {
        console.error('Error loading teams:', error);
        const tbody = document.getElementById('teamsTableBody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Error loading teams</td></tr>';
        }
    }
}

// Render teams
function renderTeams() {
    const tbody = document.getElementById('teamsTableBody');
    if (!tbody) return;
    
    if (!teamsData || teamsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">No teams found</td></tr>';
        return;
    }
    
    tbody.innerHTML = teamsData.map((team, idx) => `
        <tr>
            <td>
                ${team.logo_path ? 
                    `<img src="${team.logo_path}" alt="${team.name}" style="width:40px;height:40px;object-fit:cover;border-radius:4px;">` :
                    `<div style="width:40px;height:40px;background:#ddd;border-radius:4px;"></div>`
                }
            </td>
            <td><strong style="color:#ffd700!important">${team.name || 'Unknown'}</strong></td>
            <td><code style="background:rgba(0,0,0,0.5);color:#00d4ff!important;padding:0.25rem 0.5rem;border-radius:4px">${team.username || 'N/A'}</code></td>
            <td><span style="color:#00ff88!important;font-weight:700">₹${(team.budget || 0).toLocaleString('en-IN')}</span></td>
            <td><span style="color:#ff3366!important;font-weight:700">₹${(team.total_spent || 0).toLocaleString('en-IN')}</span></td>
            <td>
                <span style="color:#ffd700!important;font-weight:700">₹${((team.remaining_budget !== undefined ? team.remaining_budget : (team.budget || 0) - (team.total_spent || 0))).toLocaleString('en-IN')}</span>
                <div class="progress mt-1" style="height:5px;background:rgba(255,255,255,0.1)">
                    <div class="progress-bar bg-success" style="width:${team.budget > 0 ? Math.min(100, ((team.remaining_budget || 0) / team.budget * 100)) : 0}%"></div>
                </div>
            </td>
            <td><span class="badge" style="background:#ffd700!important;color:#000!important">${team.players_count || 0}</span></td>
            <td>
                <button onclick="window.editTeam('${team._id}')" class="btn btn-sm btn-outline-primary" style="margin-right:5px" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button onclick="window.deleteTeam('${team._id}','${(team.name || '').replace(/'/g, "\\'")}',${team.players_count || 0})" class="btn btn-sm btn-outline-danger" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
    
    console.log('Teams rendered');
}

// Filter teams
function filterTeams() {
    const searchInput = document.getElementById('teamSearchInput');
    if (!searchInput) return;
    
    const term = searchInput.value.toLowerCase();
    const filtered = teamsData.filter(t => 
        (t.name || '').toLowerCase().includes(term) ||
        (t.username || '').toLowerCase().includes(term)
    );
    
    const temp = teamsData;
    teamsData = filtered;
    renderTeams();
    teamsData = temp;
}

// Sort teams
function sortTeams() {
    const select = document.getElementById('teamSortSelect');
    if (!select) return;
    
    const sortBy = select.value;
    teamsData.sort((a, b) => {
        switch(sortBy) {
            case 'name': return (a.name || '').localeCompare(b.name || '');
            case 'budget': return (b.budget || 0) - (a.budget || 0);
            case 'spent': return (b.total_spent || 0) - (a.total_spent || 0);
            case 'players': return (b.players_count || 0) - (a.players_count || 0);
            default: return 0;
        }
    });
    renderTeams();
}

// Open modal
function openTeamModal() {
    document.getElementById('teamModalLabel').textContent = 'Add New Team';
    document.getElementById('teamForm').reset();
    document.getElementById('teamId').value = '';
    document.getElementById('teamPassword').required = true;
    document.getElementById('passwordRequired').textContent = '*';
    document.getElementById('passwordHint').textContent = 'Minimum 6 characters';
    document.getElementById('teamLogoPreview').src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Crect fill='%23e9ecef' width='120' height='120'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-size='14' fill='%23666'%3ENo Logo%3C/text%3E%3C/svg%3E";
    document.getElementById('teamLogo').value = '';
    teamModal.show();
}

// Edit team
async function editTeam(teamId) {
    console.log('Edit team:', teamId);
    try {
        const response = await window.api(`/teams/${teamId}`);
        if (!response.ok) throw new Error('Failed to load team');
        
        const team = await response.json();
        
        document.getElementById('teamModalLabel').textContent = 'Edit Team';
        document.getElementById('teamId').value = team._id;
        document.getElementById('teamName').value = team.name;
        document.getElementById('teamUsername').value = team.username;
        document.getElementById('teamBudget').value = team.budget;
        document.getElementById('teamLogo').value = team.logo_path || '';
        document.getElementById('teamPassword').value = '';
        document.getElementById('teamPassword').required = false;
        document.getElementById('passwordRequired').textContent = '';
        document.getElementById('passwordHint').textContent = 'Leave blank to keep current password';
        
        const preview = document.getElementById('teamLogoPreview');
        preview.src = team.logo_path || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Crect fill='%23e9ecef' width='120' height='120'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-size='14' fill='%23666'%3ENo Logo%3C/text%3E%3C/svg%3E";
        
        teamModal.show();
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to load team data');
    }
}

// Save team
async function saveTeam() {
    const teamId = document.getElementById('teamId').value;
    const name = document.getElementById('teamName').value.trim();
    const username = document.getElementById('teamUsername').value.trim();
    const password = document.getElementById('teamPassword').value;
    const budget = document.getElementById('teamBudget').value;
    const logo = document.getElementById('teamLogo').value.trim();
    
    if (!name || !username || !budget) {
        alert('Please fill all required fields');
        return;
    }
    
    if (!teamId && !password) {
        alert('Password is required for new teams');
        return;
    }
    
    if (password && password.length < 6) {
        alert('Password must be at least 6 characters');
        return;
    }
    
    const formData = new FormData();
    formData.append('name', name);
    formData.append('username', username);
    formData.append('budget', budget);
    if (logo) formData.append('logo_path', logo);
    if (password) formData.append('password', password);
    
    try {
        const url = teamId ? `/teams/update/${teamId}` : '/teams/create';
        const method = teamId ? 'PUT' : 'POST';
        
        const response = await window.api(url, { method, body: formData });
        const result = await response.json();
        
        if (!response.ok) throw new Error(result.detail || 'Failed to save team');
        
        alert('✅ ' + (result.message || 'Team saved successfully'));
        teamModal.hide();
        loadTeams();
    } catch (error) {
        console.error('Error:', error);
        alert('❌ ' + error.message);
    }
}

// Delete team
function deleteTeam(teamId, teamName, playersCount) {
    console.log('Delete team:', teamId, teamName);
    deleteTeamId = teamId;
    document.getElementById('deleteTeamName').textContent = teamName;
    
    const warning = document.getElementById('deleteWarning');
    if (playersCount > 0) {
        warning.textContent = `Warning: This team has ${playersCount} purchased players. Deletion will be prevented.`;
        warning.className = 'text-danger';
    } else {
        warning.textContent = 'This action cannot be undone.';
        warning.className = 'text-muted';
    }
    
    deleteModal.show();
}

// Confirm delete
async function confirmDelete() {
    if (!deleteTeamId) return;
    
    try {
        const response = await window.api(`/teams/delete/${deleteTeamId}`, { method: 'DELETE' });
        const result = await response.json();
        
        if (!response.ok) throw new Error(result.detail || 'Failed to delete team');
        
        alert('✅ ' + (result.message || 'Team deleted successfully'));
        deleteModal.hide();
        deleteTeamId = null;
        loadTeams();
    } catch (error) {
        console.error('Error:', error);
        alert('❌ ' + error.message);
    }
}

// Preview logo
function previewLogo(input) {
    const preview = document.getElementById('teamLogoPreview');
    const logoData = document.getElementById('teamLogo');
    
    if (input.files && input.files[0]) {
        const file = input.files[0];
        
        if (file.size > 2 * 1024 * 1024) {
            alert('File size must be less than 2MB');
            input.value = '';
            return;
        }
        
        if (!file.type.match('image.*')) {
            alert('Please select an image file');
            input.value = '';
            return;
        }
        
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            logoData.value = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

// Expose functions globally
window.previewLogo = previewLogo;
window.loadTeams = loadTeams;
window.filterTeams = filterTeams;
window.sortTeams = sortTeams;
window.openTeamModal = openTeamModal;
window.editTeam = editTeam;
window.saveTeam = saveTeam;
window.deleteTeam = deleteTeam;
window.confirmDelete = confirmDelete;

console.log('Admin teams module loaded');
