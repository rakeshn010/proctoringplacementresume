"""
Security utilities for authentication and authorization.
Handles JWT tokens, password hashing, and role-based access control.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
import bcrypt
from fastapi import HTTPException, Header, Depends, status, Request
from bson import ObjectId

from core.config import settings
from database import db


def hash_password(password: str) -> str:
    """Hash a plain password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def create_access_token(
    subject: str,
    extra_data: Optional[Dict[str, Any]] = None
) -> str:
    """Create a JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    
    payload = {
        "sub": subject,
        "typ": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    
    if extra_data:
        payload.update(extra_data)
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Create a JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    
    payload = {
        "sub": subject,
        "typ": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Dependency to get the current authenticated user.
    Validates JWT token from Authorization header or cookies.
    Uses request state set by auth middleware if available.
    """
    # First, check if auth middleware already validated the user
    if hasattr(request.state, "is_authenticated") and request.state.is_authenticated:
        return {
            "user_id": request.state.user_id,
            "email": request.state.user_email,
            "name": "",
            "is_admin": getattr(request.state, "is_admin", False),
            "team_id": getattr(request.state, "team_id", None),
            "role": request.state.user_role
        }
    
    # Fallback: Try to get token from Authorization header or cookies
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    elif hasattr(request, "cookies"):
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header"
        )
    
    payload = decode_token(token)
    
    if payload.get("typ") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Check if this is a team token
    token_role = payload.get("role")
    
    if token_role == "team":
        # Fetch team from database
        try:
            team = db.teams.find_one({"_id": ObjectId(user_id)})
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid team ID"
            )
        
        if not team:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Team not found"
            )
        
        return {
            "user_id": str(team["_id"]),
            "email": team.get("username", ""),
            "name": team.get("name", ""),
            "is_admin": False,
            "team_id": str(team["_id"]),
            "role": "team_member"
        }
    else:
        # Fetch user from database
        try:
            user = db.users.find_one({"_id": ObjectId(user_id), "is_active": True})
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID"
            )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return {
            "user_id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("name", ""),
            "is_admin": bool(user.get("is_admin", False)),
            "team_id": str(user["team_id"]) if user.get("team_id") else None,
            "role": user.get("role", "viewer")
        }


def require_admin(current_user: Dict = Depends(get_current_user)):
    """Dependency to require admin privileges."""
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


def require_team_member(current_user: Dict = Depends(get_current_user)):
    """Dependency to require team membership."""
    if not current_user.get("team_id") and not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team membership required"
        )
    return current_user
