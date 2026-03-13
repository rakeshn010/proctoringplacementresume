/**
 * Team Chat System
 * Version: 1.0.0
 */

let currentRoom = 'global';
let chatMessages = [];
let chatWs = null;

// Initialize chat
function initChat() {
    loadChatRooms();
    loadChatMessages();
    connectChatWebSocket();
    
    // Setup send button
    const sendBtn = document.getElementById('chat-send-btn');
    if (sendBtn) {
        sendBtn.addEventListener('click', sendChatMessage);
    }
    
    // Setup enter key
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });
    }
}

// Load chat rooms
async function loadChatRooms() {
    try {
        const res = await api('/chat/rooms');
        const data = await res.json();
        
        if (data.ok) {
            renderChatRooms(data.rooms);
        }
    } catch (error) {
        console.error('Error loading chat rooms:', error);
    }
}

// Render chat rooms
function renderChatRooms(rooms) {
    const container = document.getElementById('chat-rooms-list');
    if (!container) return;
    
    container.innerHTML = rooms.map(room => `
        <div class="chat-room-item ${room.id === currentRoom ? 'active' : ''}" 
             onclick="switchChatRoom('${room.id}')">
            <div class="chat-room-name">${room.name}</div>
            <div class="chat-room-desc">${room.description}</div>
        </div>
    `).join('');
}

// Switch chat room
function switchChatRoom(roomId) {
    currentRoom = roomId;
    loadChatMessages();
    loadChatRooms(); // Refresh to update active state
}

// Load chat messages
async function loadChatMessages() {
    try {
        const res = await api(`/chat/messages?room=${currentRoom}&limit=50`);
        const data = await res.json();
        
        if (data.ok) {
            chatMessages = data.messages;
            renderChatMessages();
        }
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

// Render chat messages
function renderChatMessages() {
    const container = document.getElementById('chat-messages-container');
    if (!container) return;
    
    if (chatMessages.length === 0) {
        container.innerHTML = '<div class="chat-empty">No messages yet. Start the conversation!</div>';
        return;
    }
    
    container.innerHTML = chatMessages.map(msg => {
        const time = new Date(msg.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const senderClass = msg.sender_type === 'admin' ? 'admin' : 'team';
        
        return `
            <div class="chat-message ${senderClass}">
                <div class="chat-message-header">
                    <span class="chat-sender">${msg.sender_name}</span>
                    <span class="chat-time">${time}</span>
                </div>
                <div class="chat-message-text">${escapeHtml(msg.message)}</div>
            </div>
        `;
    }).join('');
    
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

// Send chat message
async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    if (!input) return;
    
    const message = input.value.trim();
    if (!message) return;
    
    try {
        const formData = new FormData();
        formData.append('message', message);
        formData.append('room', currentRoom);
        
        const res = await api('/chat/send', {
            method: 'POST',
            body: formData
        });
        
        const data = await res.json();
        
        if (data.ok) {
            input.value = '';
            // Message will be added via WebSocket
        } else {
            alert('Failed to send message');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        alert('Error sending message');
    }
}

// Connect to WebSocket for real-time chat
function connectChatWebSocket() {
    // Reuse existing WebSocket connection
    // Chat messages will come through the main WebSocket
}

// Handle incoming chat message via WebSocket
function handleChatMessage(data) {
    if (data.room === currentRoom) {
        chatMessages.push(data);
        renderChatMessages();
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Toggle chat panel
function toggleChatPanel() {
    const panel = document.getElementById('chat-panel');
    if (panel) {
        panel.classList.toggle('open');
    }
}

// Expose functions globally
window.initChat = initChat;
window.switchChatRoom = switchChatRoom;
window.sendChatMessage = sendChatMessage;
window.toggleChatPanel = toggleChatPanel;
window.handleChatMessage = handleChatMessage;
