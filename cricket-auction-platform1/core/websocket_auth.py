"""
WebSocket authentication and authorization.
Secures WebSocket connections with JWT tokens.
"""
from typing import Optional, Dict, Any
from fastapi import WebSocket, WebSocketException, status
from jose import jwt, JWTError
from bson import ObjectId
import logging

from core.config import settings
from database import db

logger = logging.getLogger(__name__)


async def authenticate_websocket(websocket: WebSocket) -> Optional[Dict[str, Any]]:
    """
    Authenticate WebSocket connection using JWT token.
    
    Token can be provided via:
    1. Query parameter: ?token=<jwt_token>
    2. First message: {"type": "auth", "token": "<jwt_token>"}
    
    Returns:
        User data dict if authenticated, None otherwise
    """
    # Try to get token from query parameters
    token = websocket.query_params.get("token")
    
    if not token:
        # Wait for auth message
        try:
            message = await websocket.receive_json()
            if message.get("type") == "auth":
                token = message.get("token")
        except Exception as e:
            logger.error(f"Error receiving auth message: {e}")
            return None
    
    if not token:
        logger.warning("No token provided for WebSocket authentication")
        return None
    
    # Validate token
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        if payload.get("typ") != "access":
            logger.warning("Invalid token type for WebSocket")
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("No user ID in token payload")
            return None
        
        # Fetch user from database
        user = db.users.find_one({"_id": ObjectId(user_id), "is_active": True})
        
        if not user:
            logger.warning(f"User not found or inactive: {user_id}")
            return None
        
        return {
            "user_id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("name", ""),
            "is_admin": bool(user.get("is_admin", False)),
            "team_id": str(user["team_id"]) if user.get("team_id") else None,
            "role": user.get("role", "viewer")
        }
        
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        return None
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None


async def require_websocket_auth(websocket: WebSocket) -> Dict[str, Any]:
    """
    Require authentication for WebSocket connection.
    Closes connection if authentication fails.
    
    Returns:
        User data dict
    
    Raises:
        WebSocketException if authentication fails
    """
    user = await authenticate_websocket(websocket)
    
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
    
    return user


async def check_websocket_permission(user: Dict[str, Any], action: str) -> bool:
    """
    Check if user has permission for specific WebSocket action.
    
    Args:
        user: User data dict
        action: Action to check (e.g., 'bid', 'admin_control')
    
    Returns:
        True if permitted, False otherwise
    """
    if action == "admin_control":
        return user.get("is_admin", False)
    
    if action == "bid":
        # Must be team member or admin
        return user.get("team_id") is not None or user.get("is_admin", False)
    
    if action == "view":
        # Everyone can view
        return True
    
    return False
