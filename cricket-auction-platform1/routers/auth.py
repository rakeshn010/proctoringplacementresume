"""
Authentication router.
Handles user registration, login, and token refresh.
"""
from fastapi import APIRouter, HTTPException, Form, Depends, status, Request, Response
from datetime import datetime, timezone
from bson import ObjectId

from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user
)
from core.password_validator import validate_password
from core.config import settings
from database import db
from schemas.user import TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(None),
    password: str = Form(None),
    name: str = Form(None)
):
    """
    Register a new user account.
    Accepts both Form data and JSON.
    """
    # If Form data not provided, try to get from JSON body
    if not email or not password:
        try:
            body = await request.json()
            email = body.get("email")
            password = body.get("password")
            name = body.get("name")
        except Exception:
            pass
    
    # Validate required fields
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email and password are required"
        )
    
    email = email.lower().strip()
    
    # Validate password strength
    validate_password(password)
    
    # Check if email already exists
    if db.users.find_one({"email": email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    is_admin = email in settings.admin_email_list
    
    user_doc = {
        "email": email,
        "password_hash": hash_password(password),
        "name": name or "",
        "is_active": True,
        "is_admin": is_admin,
        "role": "admin" if is_admin else "viewer",
        "team_id": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    db.users.create_index("email", unique=True)
    db.users.insert_one(user_doc)
    
    return {"ok": True, "message": "Registration successful. Please log in."}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: dict = Depends(get_current_user)
):
    """
    Logout - invalidate token and destroy session.
    Forces user to re-login, no auto-login.
    """
    from core.session_manager import session_manager
    
    # Get token from header or cookie
    token = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]
    elif request.cookies.get("access_token"):
        token = request.cookies.get("access_token")
    
    # Blacklist the token
    if token:
        session_manager.blacklist_token(token)
    
    # Destroy all user sessions
    user_id = current_user.get("user_id")
    if user_id:
        session_manager.destroy_all_user_sessions(user_id)
    
    # Clear cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    
    return {
        "ok": True,
        "message": "Logged out successfully. Please login again to access the system."
    }


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    email: str = Form(None),
    password: str = Form(None)
):
    """
    Login with strict security - no auto-login, no persistent sessions.
    Accepts both Form data and JSON.
    """
    # Import dependencies
    from core.rate_limiter import rate_limiter, get_client_ip
    from core.config import settings
    from core.session_manager import session_manager
    
    # If Form data not provided, try to get from JSON body
    if not email or not password:
        try:
            body = await request.json()
            email = body.get("email")
            password = body.get("password")
        except Exception:
            pass
    
    # Validate required fields
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email and password are required"
        )
    
    # Apply rate limiting if enabled
    if settings.ENABLE_RATE_LIMITING:
        client_ip = await get_client_ip(request)
        await rate_limiter.check_auth_rate_limit(client_ip)
    
    email = email.lower().strip()
    
    user = db.users.find_one({"email": email})
    
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    user_id = str(user["_id"])
    
    # Destroy any existing sessions for this user (force re-login)
    session_manager.destroy_all_user_sessions(user_id)
    
    # Create new session
    session_id = session_manager.create_session(user_id, request)
    
    # Create tokens with SHORT expiration
    access_token = create_access_token(
        subject=user_id,
        extra_data={
            "email": user["email"],
            "is_admin": bool(user.get("is_admin", False)),
            "team_id": str(user["team_id"]) if user.get("team_id") else None,
            "session_id": session_id
        }
    )
    
    refresh_token = create_refresh_token(subject=user_id)
    
    # Set tokens as HTTP-only cookies for web pages
    response.set_cookie(
        key="access_token",
        value=access_token,
        path="/",  # Available on all paths
        httponly=True,  # Prevents JavaScript access (XSS protection)
        secure=True,  # Required for HTTPS (Railway uses HTTPS)
        samesite="lax",  # CSRF protection
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 15 minutes
    )
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        path="/",  # Available on all paths
        httponly=True,
        secure=True,  # Required for HTTPS
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # 1 day
    )
    
    return {
        "ok": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
        "user": {
            "id": user_id,
            "email": user["email"],
            "name": user.get("name", ""),
            "is_admin": bool(user.get("is_admin", False)),
            "role": user.get("role", "viewer")
        }
    }


@router.post("/refresh")
async def refresh_token(refresh_token: str = Form(...)):
    """Refresh access token using refresh token."""
    payload = decode_token(refresh_token)
    
    if payload.get("typ") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    user_id = payload.get("sub")
    
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
    
    # Create new access token
    access_token = create_access_token(
        subject=user_id,
        extra_data={
            "email": user["email"],
            "is_admin": bool(user.get("is_admin", False)),
            "team_id": str(user["team_id"]) if user.get("team_id") else None
        }
    )
    
    return {
        "ok": True,
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    return {"ok": True, "user": current_user}


@router.post("/team/login")
async def team_login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    """Team login endpoint."""
    username = username.strip()
    
    team = db.teams.find_one({"username": username})
    
    if not team or not verify_password(password, team.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    team_id = str(team["_id"])
    
    # Create tokens with team role
    access_token = create_access_token(
        subject=team_id,
        extra_data={
            "username": team["username"],
            "team_name": team["name"],
            "role": "team",
            "is_admin": False
        }
    )
    
    refresh_token = create_refresh_token(subject=team_id)
    
    # Set tokens as HTTP-only cookies for web pages
    response.set_cookie(
        key="access_token",
        value=access_token,
        path="/",  # Available on all paths
        httponly=True,
        secure=True,  # Required for HTTPS
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        path="/",  # Available on all paths
        httponly=True,
        secure=True,  # Required for HTTPS
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    return {
        "ok": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "team_id": team_id,
        "team_name": team["name"]
    }
