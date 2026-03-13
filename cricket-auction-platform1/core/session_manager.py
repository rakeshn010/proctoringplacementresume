"""
Strict Session Management
No auto-login, force re-authentication, short token expiration.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Request, Response, HTTPException, status
import secrets
import hashlib
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Strict session management with:
    - No persistent sessions (no "remember me")
    - Short token expiration
    - Force logout on browser close
    - No auto-login
    - Session invalidation on logout
    """
    
    # Active sessions: {session_id: {user_id, created_at, last_activity, ip, user_agent}}
    active_sessions: Dict[str, Dict[str, Any]] = {}
    
    # Blacklisted tokens (logged out)
    blacklisted_tokens: set = set()
    
    # Session settings
    SESSION_TIMEOUT_MINUTES = 30  # Auto logout after 30 minutes of inactivity
    MAX_SESSION_DURATION_HOURS = 8  # Force logout after 8 hours
    
    @staticmethod
    def create_session(user_id: str, request: Request) -> str:
        """
        Create a new session.
        Returns session ID.
        """
        session_id = secrets.token_urlsafe(32)
        
        SessionManager.active_sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown")
        }
        
        logger.info(f"Session created: {session_id[:8]}... for user {user_id}")
        return session_id
    
    @staticmethod
    def validate_session(session_id: str, request: Request) -> Optional[str]:
        """
        Validate session and return user_id if valid.
        Returns None if invalid or expired.
        """
        if not session_id or session_id not in SessionManager.active_sessions:
            return None
        
        session = SessionManager.active_sessions[session_id]
        now = datetime.now(timezone.utc)
        
        # Check if session expired due to inactivity
        last_activity = session["last_activity"]
        if now - last_activity > timedelta(minutes=SessionManager.SESSION_TIMEOUT_MINUTES):
            logger.info(f"Session expired (inactivity): {session_id[:8]}...")
            SessionManager.destroy_session(session_id)
            return None
        
        # Check if session exceeded maximum duration
        created_at = session["created_at"]
        if now - created_at > timedelta(hours=SessionManager.MAX_SESSION_DURATION_HOURS):
            logger.info(f"Session expired (max duration): {session_id[:8]}...")
            SessionManager.destroy_session(session_id)
            return None
        
        # Verify IP hasn't changed (security)
        current_ip = request.client.host if request.client else "unknown"
        if session["ip"] != current_ip:
            logger.warning(
                f"Session IP mismatch: {session_id[:8]}... "
                f"Expected {session['ip']}, got {current_ip}"
            )
            SessionManager.destroy_session(session_id)
            return None
        
        # Update last activity
        session["last_activity"] = now
        
        return session["user_id"]
    
    @staticmethod
    def destroy_session(session_id: str):
        """Destroy a session."""
        if session_id in SessionManager.active_sessions:
            del SessionManager.active_sessions[session_id]
            logger.info(f"Session destroyed: {session_id[:8]}...")
    
    @staticmethod
    def destroy_all_user_sessions(user_id: str):
        """Destroy all sessions for a user."""
        sessions_to_remove = [
            sid for sid, session in SessionManager.active_sessions.items()
            if session["user_id"] == user_id
        ]
        
        for session_id in sessions_to_remove:
            SessionManager.destroy_session(session_id)
        
        logger.info(f"Destroyed {len(sessions_to_remove)} sessions for user {user_id}")
    
    @staticmethod
    def blacklist_token(token: str):
        """Add token to blacklist (for logout)."""
        # Hash token for storage (don't store full token)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        SessionManager.blacklisted_tokens.add(token_hash)
        logger.info(f"Token blacklisted: {token_hash[:8]}...")
    
    @staticmethod
    def is_token_blacklisted(token: str) -> bool:
        """Check if token is blacklisted."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return token_hash in SessionManager.blacklisted_tokens
    
    @staticmethod
    def cleanup_expired_sessions():
        """Remove expired sessions (run periodically)."""
        now = datetime.now(timezone.utc)
        expired = []
        
        for session_id, session in SessionManager.active_sessions.items():
            last_activity = session["last_activity"]
            if now - last_activity > timedelta(minutes=SessionManager.SESSION_TIMEOUT_MINUTES):
                expired.append(session_id)
        
        for session_id in expired:
            SessionManager.destroy_session(session_id)
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
    
    @staticmethod
    def get_active_session_count() -> int:
        """Get number of active sessions."""
        return len(SessionManager.active_sessions)
    
    @staticmethod
    def get_user_session_count(user_id: str) -> int:
        """Get number of active sessions for a user."""
        return sum(
            1 for session in SessionManager.active_sessions.values()
            if session["user_id"] == user_id
        )


# Global session manager instance
session_manager = SessionManager()
