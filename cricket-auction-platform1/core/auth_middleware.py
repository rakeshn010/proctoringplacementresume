"""
Strict Authentication Middleware
Forces re-authentication, no auto-login, validates every request.
"""
from fastapi import Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
from jose import jwt, JWTError
from bson import ObjectId
import logging

from core.config import settings
from core.session_manager import session_manager
from core.route_guard import RouteGuard, check_route_access
from database import db

logger = logging.getLogger(__name__)


class StrictAuthMiddleware(BaseHTTPMiddleware):
    """
    Strict authentication middleware that:
    1. Validates JWT tokens on every request
    2. Checks token blacklist (logout)
    3. Validates session (no auto-login)
    4. Enforces route protection
    5. Blocks unauthorized access
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip authentication for public routes
        if RouteGuard.is_public_route(request.url.path):
            return await call_next(request)
        
        # Initialize request state
        request.state.user_id = None
        request.state.user_email = None
        request.state.user_role = None
        request.state.is_authenticated = False
        
        # Try to get token from multiple sources
        token = None
        
        # 1. Authorization header (for API requests)
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]
            logger.debug(f"Token from Authorization header for {request.url.path}")
        
        # 2. Cookie (for web pages)
        if not token:
            token = request.cookies.get("access_token")
            if token:
                logger.debug(f"Token from cookie for {request.url.path}")
        
        # If no token, check if route requires authentication
        if not token:
            logger.warning(f"No token found for {request.url.path}")
            # Check if this route is protected
            required_roles = RouteGuard.get_required_roles(request.url.path)
            if required_roles:
                # Protected route without token - redirect to login
                if request.url.path.startswith("/api/"):
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Authentication required"}
                    )
                else:
                    logger.warning(f"Redirecting {request.url.path} to login (no token)")
                    return RedirectResponse(
                        url="/?error=login_required",
                        status_code=303
                    )
            
            # Not protected, allow access
            return await call_next(request)
        
        # Validate token
        try:
            # Check if token is blacklisted (logged out)
            if session_manager.is_token_blacklisted(token):
                logger.warning("Blacklisted token used")
                return self._handle_invalid_auth(request)
            
            # Decode token
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Validate token type
            if payload.get("typ") != "access":
                logger.warning("Invalid token type")
                return self._handle_invalid_auth(request)
            
            # Get user ID
            user_id = payload.get("sub")
            if not user_id:
                logger.warning("No user ID in token")
                return self._handle_invalid_auth(request)
            
            # Check if this is a team token (has "role": "team" in payload)
            token_role = payload.get("role")
            
            if token_role == "team":
                # This is a team token - fetch from teams collection
                try:
                    team = db.teams.find_one({"_id": ObjectId(user_id)})
                except Exception:
                    logger.error(f"Invalid team ID format: {user_id}")
                    return self._handle_invalid_auth(request)
                
                if not team:
                    logger.warning(f"Team not found: {user_id}")
                    return self._handle_invalid_auth(request)
                
                # Set team info in request state
                request.state.user_id = str(team["_id"])
                request.state.user_email = team.get("username", "")
                request.state.user_role = "team_member"
                request.state.is_admin = False
                request.state.is_authenticated = True
                request.state.team_id = str(team["_id"])
            else:
                # This is a user token - fetch from users collection
                try:
                    user = db.users.find_one({
                        "_id": ObjectId(user_id),
                        "is_active": True
                    })
                except Exception:
                    logger.error(f"Invalid user ID format: {user_id}")
                    return self._handle_invalid_auth(request)
                
                if not user:
                    logger.warning(f"User not found or inactive: {user_id}")
                    return self._handle_invalid_auth(request)
                
                # Set user info in request state
                request.state.user_id = str(user["_id"])
                request.state.user_email = user["email"]
                request.state.user_role = user.get("role", "viewer")
                request.state.is_admin = bool(user.get("is_admin", False))
                request.state.is_authenticated = True
            
            # Check route access
            access_check = await check_route_access(request)
            if access_check:
                return access_check
            
            # Proceed with request
            response = await call_next(request)
            
            # Add security headers to response
            response.headers["X-User-Role"] = request.state.user_role
            
            return response
            
        except JWTError as e:
            logger.warning(f"JWT validation error: {e}")
            return self._handle_invalid_auth(request)
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return self._handle_invalid_auth(request)
    
    def _handle_invalid_auth(self, request: Request):
        """Handle invalid authentication."""
        # Clear any auth cookies
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired authentication"}
            )
        else:
            response = RedirectResponse(
                url="/?error=session_expired",
                status_code=303
            )
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            return response
