"""
Advanced Route Protection System
Prevents unauthorized access to protected pages and endpoints.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class RouteGuard:
    """
    Route protection system that prevents unauthorized access.
    Blocks users from accessing pages by typing URLs directly.
    """
    
    # Define protected routes and their required roles
    PROTECTED_ROUTES = {
        "/admin": ["admin"],
        "/live": ["admin", "team_member", "viewer"],
        "/team/dashboard": ["admin", "team_member"],
        "/security/dashboard": ["admin"],
    }
    
    # Public routes (no authentication required)
    PUBLIC_ROUTES = [
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    ]
    
    # API routes (checked via JWT in headers, not cookies)
    API_PREFIXES = [
        "/auth/",
        "/api/",
        "/teams/",
        "/players/",
        "/auction/",
        "/admin/",
        "/reports/",
        "/viewer/",
    ]
    
    @staticmethod
    def is_public_route(path: str) -> bool:
        """Check if route is public."""
        # Exact match
        if path in RouteGuard.PUBLIC_ROUTES:
            return True
        
        # Static files
        if path.startswith("/static/"):
            return True
        
        # API routes (protected by JWT in headers)
        for prefix in RouteGuard.API_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False
    
    @staticmethod
    def get_required_roles(path: str) -> Optional[List[str]]:
        """Get required roles for a route."""
        # Check exact match
        if path in RouteGuard.PROTECTED_ROUTES:
            return RouteGuard.PROTECTED_ROUTES[path]
        
        # Check prefix match
        for route, roles in RouteGuard.PROTECTED_ROUTES.items():
            if path.startswith(route):
                return roles
        
        return None
    
    @staticmethod
    def verify_access(path: str, user_role: Optional[str]) -> bool:
        """
        Verify if user has access to the route.
        
        Args:
            path: Request path
            user_role: User's role (admin, team_member, viewer, None)
        
        Returns:
            True if access allowed, False otherwise
        """
        # Public routes - always allow
        if RouteGuard.is_public_route(path):
            return True
        
        # Get required roles for this route
        required_roles = RouteGuard.get_required_roles(path)
        
        # If route is not protected, allow access
        if required_roles is None:
            return True
        
        # If route is protected but user not authenticated, deny
        if user_role is None:
            return False
        
        # Check if user's role is in required roles
        return user_role in required_roles


async def check_route_access(request: Request) -> Optional[RedirectResponse]:
    """
    Middleware function to check route access.
    Returns RedirectResponse if access denied, None if allowed.
    """
    path = request.url.path
    
    # Skip public routes
    if RouteGuard.is_public_route(path):
        return None
    
    # Get user role from request state (set by auth middleware)
    user_role = getattr(request.state, "user_role", None)
    user_email = getattr(request.state, "user_email", None)
    
    # Verify access
    if not RouteGuard.verify_access(path, user_role):
        logger.warning(
            f"Access denied: {path} for user {user_email or 'anonymous'} "
            f"with role {user_role or 'none'}"
        )
        
        # Redirect to home page with error
        return RedirectResponse(
            url="/?error=unauthorized",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    return None
