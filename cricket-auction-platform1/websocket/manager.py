"""
WebSocket connection manager for real-time auction updates.
Handles multiple concurrent connections and broadcasts events.
Enhanced with compression, heartbeat, and better error handling.
"""
import asyncio
import json
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket
from datetime import datetime, timezone
import logging
import gzip

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts.
    Enhanced with:
    - Message compression for large payloads
    - Heartbeat/ping-pong for connection health
    - Connection pooling and cleanup
    - Selective broadcasting (room-based)
    """
    
    def __init__(self):
        # Active connections: {connection_id: {"ws": WebSocket, "user": dict, "last_ping": datetime}}
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        # User to connection mapping
        self.user_connections: Dict[str, Set[str]] = {}
        # Room-based connections (e.g., team rooms)
        self.rooms: Dict[str, Set[str]] = {}
        # Auction timer task
        self.timer_task: Optional[asyncio.Task] = None
        self.timer_seconds: int = 0
        self.timer_running: bool = False
        # Heartbeat task
        self.heartbeat_task: Optional[asyncio.Task] = None
        # Message queue for batching
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.batch_task: Optional[asyncio.Task] = None
        
    async def connect(
        self, 
        websocket: WebSocket, 
        connection_id: str, 
        user_data: Optional[Dict] = None
    ):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        self.active_connections[connection_id] = {
            "ws": websocket,
            "user": user_data,
            "last_ping": datetime.now(timezone.utc),
            "authenticated": user_data is not None
        }
        
        if user_data:
            user_id = user_data.get("user_id")
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(connection_id)
                
                # Add to team room if applicable
                team_id = user_data.get("team_id")
                if team_id:
                    await self.join_room(connection_id, f"team_{team_id}")
        
        logger.info(f"WebSocket connected: {connection_id} (user: {user_data.get('email') if user_data else 'anonymous'})")
        
        # Start heartbeat if not running
        if not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connected",
            "connection_id": connection_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, connection_id)
        
    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection."""
        if connection_id in self.active_connections:
            conn_data = self.active_connections[connection_id]
            user_data = conn_data.get("user")
            
            if user_data:
                user_id = user_data.get("user_id")
                if user_id and user_id in self.user_connections:
                    self.user_connections[user_id].discard(connection_id)
                    if not self.user_connections[user_id]:
                        del self.user_connections[user_id]
                
                # Remove from team room
                team_id = user_data.get("team_id")
                if team_id:
                    room_name = f"team_{team_id}"
                    if room_name in self.rooms:
                        self.rooms[room_name].discard(connection_id)
            
            del self.active_connections[connection_id]
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def join_room(self, connection_id: str, room_name: str):
        """Add connection to a room for selective broadcasting."""
        if room_name not in self.rooms:
            self.rooms[room_name] = set()
        self.rooms[room_name].add(connection_id)
        logger.debug(f"Connection {connection_id} joined room {room_name}")
    
    async def leave_room(self, connection_id: str, room_name: str):
        """Remove connection from a room."""
        if room_name in self.rooms:
            self.rooms[room_name].discard(connection_id)
            if not self.rooms[room_name]:
                del self.rooms[room_name]
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat to detect dead connections."""
        while True:
            try:
                await asyncio.sleep(15)  # Every 15 seconds (faster detection)
                
                now = datetime.now(timezone.utc)
                disconnected = []
                
                for connection_id, conn_data in self.active_connections.items():
                    try:
                        # Send ping
                        await conn_data["ws"].send_json({"type": "ping"})
                        conn_data["last_ping"] = now
                    except Exception as e:
                        logger.warning(f"Heartbeat failed for {connection_id}: {e}")
                        disconnected.append(connection_id)
                
                # Clean up dead connections
                for connection_id in disconnected:
                    self.disconnect(connection_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
    
    async def send_personal_message(self, message: dict, connection_id: str, compress: bool = False):
        """Send a message to a specific connection with optional compression."""
        if connection_id in self.active_connections:
            try:
                conn_data = self.active_connections[connection_id]
                
                if compress and len(json.dumps(message)) > 1024:
                    # Compress large messages
                    compressed = gzip.compress(json.dumps(message).encode())
                    await conn_data["ws"].send_bytes(compressed)
                else:
                    await conn_data["ws"].send_json(message)
                    
            except Exception as e:
                logger.error(f"Error sending to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def broadcast(self, message: dict, exclude: Optional[Set[str]] = None, compress: bool = False):
        """Broadcast a message to all connected clients with optional compression."""
        exclude = exclude or set()
        disconnected = []
        
        # Prepare message once
        if compress:
            message_json = json.dumps(message)
            if len(message_json) > 1024:
                compressed_data = gzip.compress(message_json.encode())
                use_compression = True
            else:
                use_compression = False
        else:
            use_compression = False
        
        for connection_id, conn_data in self.active_connections.items():
            if connection_id in exclude:
                continue
            
            try:
                if use_compression:
                    await conn_data["ws"].send_bytes(compressed_data)
                else:
                    await conn_data["ws"].send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Clean up disconnected clients
        for connection_id in disconnected:
            self.disconnect(connection_id)
    
    async def broadcast_to_room(self, room_name: str, message: dict, compress: bool = False):
        """Broadcast message to all connections in a specific room."""
        if room_name not in self.rooms:
            return
        
        disconnected = []
        
        for connection_id in self.rooms[room_name]:
            if connection_id in self.active_connections:
                try:
                    await self.send_personal_message(message, connection_id, compress)
                except Exception as e:
                    logger.error(f"Error broadcasting to room {room_name}, connection {connection_id}: {e}")
                    disconnected.append(connection_id)
        
        # Clean up
        for connection_id in disconnected:
            self.disconnect(connection_id)
    
    async def broadcast_to_users(self, message: dict, user_ids: Set[str]):
        """Broadcast a message to specific users."""
        for user_id in user_ids:
            if user_id in self.user_connections:
                for connection_id in self.user_connections[user_id]:
                    await self.send_personal_message(message, connection_id)
    
    async def broadcast_bid(self, bid_data: dict):
        """Broadcast a new bid to all clients (high priority)."""
        message = {
            "type": "bid_placed",
            "data": bid_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "priority": "high"
        }
        await self.broadcast(message, compress=False)  # Don't compress time-sensitive data
    
    async def broadcast_player_sold(self, player_data: dict):
        """Broadcast player sold event."""
        message = {
            "type": "player_sold",
            "data": player_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast(message)
    
    async def broadcast_player_unsold(self, player_data: dict):
        """Broadcast player unsold event."""
        message = {
            "type": "player_unsold",
            "data": player_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast(message)
    
    async def broadcast_current_player(self, player_data: dict):
        """Broadcast current auction player change."""
        message = {
            "type": "current_player_changed",
            "data": player_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast(message)
    
    async def broadcast_auction_status(self, active: bool):
        """Broadcast auction status change."""
        message = {
            "type": "auction_status",
            "data": {"active": active},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast(message)
    
    async def broadcast_timer(self, seconds: int):
        """Broadcast timer update."""
        message = {
            "type": "timer_update",
            "data": {"seconds": seconds},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast(message)
    
    async def broadcast_team_update(self, team_data: dict):
        """Broadcast team budget/purse update."""
        message = {
            "type": "team_update",
            "data": team_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast(message)
    
    async def start_timer(self, seconds: int, on_complete_callback=None):
        """Start auction countdown timer."""
        if self.timer_running:
            return
        
        self.timer_seconds = seconds
        self.timer_running = True
        
        async def countdown():
            while self.timer_seconds > 0 and self.timer_running:
                await self.broadcast_timer(self.timer_seconds)
                await asyncio.sleep(1)
                self.timer_seconds -= 1
            
            if self.timer_running:
                await self.broadcast_timer(0)
                self.timer_running = False
                
                if on_complete_callback:
                    await on_complete_callback()
        
        self.timer_task = asyncio.create_task(countdown())
    
    def reset_timer(self, seconds: int):
        """Reset the auction timer."""
        self.timer_seconds = seconds
    
    def stop_timer(self):
        """Stop the auction timer."""
        self.timer_running = False
        if self.timer_task:
            self.timer_task.cancel()
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
    
    def get_authenticated_count(self) -> int:
        """Get the number of authenticated connections."""
        return sum(1 for conn in self.active_connections.values() if conn.get("authenticated"))
    
    def get_room_count(self, room_name: str) -> int:
        """Get the number of connections in a room."""
        return len(self.rooms.get(room_name, set()))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics."""
        return {
            "total_connections": self.get_connection_count(),
            "authenticated_connections": self.get_authenticated_count(),
            "unique_users": len(self.user_connections),
            "active_rooms": len(self.rooms),
            "timer_running": self.timer_running,
            "timer_seconds": self.timer_seconds
        }


# Global connection manager instance
manager = ConnectionManager()
