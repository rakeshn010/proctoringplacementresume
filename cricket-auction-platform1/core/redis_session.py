"""
Redis-based session storage for production.
Replaces in-memory sessions with persistent Redis storage.
"""
import json
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Request
import logging

logger = logging.getLogger(__name__)

# Try to import Redis, fall back to in-memory if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory sessions")


class RedisSessionManager:
    """
    Redis-based session management with fallback to in-memory.
    Provides persistent sessions across server restarts.
    """
    
    def __init__(self):
        self.redis_client = None
        self.in_memory_sessions = {}  # Fallback
        self.blacklisted_tokens = set()
        
        # Session settings
        self.SESSION_TIMEOUT_MINUTES = 30
        self.MAX_SESSION_DURATION_HOURS = 8
        
        # Initialize Redis if available
        if REDIS_AVAILABLE:
            self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection."""
        from core.config import settings
        
        if not settings.ENABLE_REDIS:
            logger.info("Redis disabled in configuration")
            return
        
        try:
            # Parse Redis URL
            redis_url = settings.REDIS_URL
            
            # Create Redis client
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Falling back to in-memory sessions")
            self.redis_client = None
    
    def create_session(self, user_id: str, request: Request) -> str:
        """Create a new session."""
        session_id = secrets.token_urlsafe(32)
        
        session_data = {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown")
        }
        
        if self.redis_client:
            # Store in Redis with TTL
            try:
                key = f"session:{session_id}"
                self.redis_client.setex(
                    key,
                    self.SESSION_TIMEOUT_MINUTES * 60,
                    json.dumps(session_data)
                )
                logger.info(f"Session created in Redis: {session_id[:8]}... for user {user_id}")
            except Exception as e:
                logger.error(f"Redis error, falling back to memory: {e}")
                self.in_memory_sessions[session_id] = session_data
        else:
            # Store in memory
            self.in_memory_sessions[session_id] = session_data
            logger.info(f"Session created in memory: {session_id[:8]}... for user {user_id}")
        
        return session_id
    
    def validate_session(self, session_id: str, request: Request) -> Optional[str]:
        """Validate session and return user_id if valid."""
        if not session_id:
            return None
        
        session_data = None
        
        # Try Redis first
        if self.redis_client:
            try:
                key = f"session:{session_id}"
                data = self.redis_client.get(key)
                if data:
                    session_data = json.loads(data)
            except Exception as e:
                logger.error(f"Redis error: {e}")
        
        # Fall back to memory
        if not session_data:
            session_data = self.in_memory_sessions.get(session_id)
        
        if not session_data:
            return None
        
        now = datetime.now(timezone.utc)
        
        # Parse timestamps
        last_activity = datetime.fromisoformat(session_data["last_activity"])
        created_at = datetime.fromisoformat(session_data["created_at"])
        
        # Check inactivity timeout
        if now - last_activity > timedelta(minutes=self.SESSION_TIMEOUT_MINUTES):
            logger.info(f"Session expired (inactivity): {session_id[:8]}...")
            self.destroy_session(session_id)
            return None
        
        # Check max duration
        if now - created_at > timedelta(hours=self.MAX_SESSION_DURATION_HOURS):
            logger.info(f"Session expired (max duration): {session_id[:8]}...")
            self.destroy_session(session_id)
            return None
        
        # Verify IP
        current_ip = request.client.host if request.client else "unknown"
        if session_data["ip"] != current_ip:
            logger.warning(f"Session IP mismatch: {session_id[:8]}...")
            self.destroy_session(session_id)
            return None
        
        # Update last activity
        session_data["last_activity"] = now.isoformat()
        
        if self.redis_client:
            try:
                key = f"session:{session_id}"
                self.redis_client.setex(
                    key,
                    self.SESSION_TIMEOUT_MINUTES * 60,
                    json.dumps(session_data)
                )
            except Exception as e:
                logger.error(f"Redis error updating session: {e}")
        else:
            self.in_memory_sessions[session_id] = session_data
        
        return session_data["user_id"]
    
    def destroy_session(self, session_id: str):
        """Destroy a session."""
        if self.redis_client:
            try:
                key = f"session:{session_id}"
                self.redis_client.delete(key)
                logger.info(f"Session destroyed in Redis: {session_id[:8]}...")
            except Exception as e:
                logger.error(f"Redis error destroying session: {e}")
        
        if session_id in self.in_memory_sessions:
            del self.in_memory_sessions[session_id]
            logger.info(f"Session destroyed in memory: {session_id[:8]}...")
    
    def destroy_all_user_sessions(self, user_id: str):
        """Destroy all sessions for a user."""
        count = 0
        
        # Redis sessions
        if self.redis_client:
            try:
                # Scan for user sessions
                for key in self.redis_client.scan_iter(match="session:*"):
                    data = self.redis_client.get(key)
                    if data:
                        session_data = json.loads(data)
                        if session_data.get("user_id") == user_id:
                            self.redis_client.delete(key)
                            count += 1
            except Exception as e:
                logger.error(f"Redis error destroying user sessions: {e}")
        
        # Memory sessions
        sessions_to_remove = [
            sid for sid, session in self.in_memory_sessions.items()
            if session["user_id"] == user_id
        ]
        
        for session_id in sessions_to_remove:
            del self.in_memory_sessions[session_id]
            count += 1
        
        logger.info(f"Destroyed {count} sessions for user {user_id}")
    
    def blacklist_token(self, token: str):
        """Add token to blacklist."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        if self.redis_client:
            try:
                key = f"blacklist:{token_hash}"
                # Store for 24 hours (longer than token expiration)
                self.redis_client.setex(key, 86400, "1")
                logger.info(f"Token blacklisted in Redis: {token_hash[:8]}...")
            except Exception as e:
                logger.error(f"Redis error blacklisting token: {e}")
                self.blacklisted_tokens.add(token_hash)
        else:
            self.blacklisted_tokens.add(token_hash)
            logger.info(f"Token blacklisted in memory: {token_hash[:8]}...")
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Check Redis
        if self.redis_client:
            try:
                key = f"blacklist:{token_hash}"
                return self.redis_client.exists(key) > 0
            except Exception as e:
                logger.error(f"Redis error checking blacklist: {e}")
        
        # Check memory
        return token_hash in self.blacklisted_tokens
    
    def get_active_session_count(self) -> int:
        """Get number of active sessions."""
        if self.redis_client:
            try:
                count = 0
                for _ in self.redis_client.scan_iter(match="session:*"):
                    count += 1
                return count
            except Exception as e:
                logger.error(f"Redis error counting sessions: {e}")
        
        return len(self.in_memory_sessions)
    
    def get_user_session_count(self, user_id: str) -> int:
        """Get number of active sessions for a user."""
        count = 0
        
        if self.redis_client:
            try:
                for key in self.redis_client.scan_iter(match="session:*"):
                    data = self.redis_client.get(key)
                    if data:
                        session_data = json.loads(data)
                        if session_data.get("user_id") == user_id:
                            count += 1
            except Exception as e:
                logger.error(f"Redis error counting user sessions: {e}")
        
        # Add memory sessions
        count += sum(
            1 for session in self.in_memory_sessions.values()
            if session["user_id"] == user_id
        )
        
        return count


# Global session manager instance
redis_session_manager = RedisSessionManager()
