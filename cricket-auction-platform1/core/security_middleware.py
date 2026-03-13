"""
Security middleware for enhanced protection.
Includes CSRF protection, security headers, and request validation.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import secrets
import hashlib
import time
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    Protects against common web vulnerabilities.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy - Allow common CDNs, Cloudinary, and Unsplash
        # Updated: 2026-02-18
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https: https://res.cloudinary.com https://images.unsplash.com; "
            "font-src 'self' data: https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "connect-src 'self' ws: wss: https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://res.cloudinary.com https://images.unsplash.com; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        response.headers["X-CSP-Version"] = "2026-02-18-v3"  # Debug header
        
        # Prevent caching of HTML pages to ensure CSP updates are applied
        if "text/html" in response.headers.get("content-type", ""):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate and sanitize incoming requests.
    Prevents common injection attacks.
    """
    
    # Suspicious patterns
    SUSPICIOUS_PATTERNS = [
        "<script", "javascript:", "onerror=", "onload=",
        "../", "..\\", "etc/passwd", "cmd.exe",
        "SELECT * FROM", "DROP TABLE", "UNION SELECT",
        "<?php", "eval(", "exec(", "system("
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request too large"}
            )
        
        # Check for suspicious patterns in URL
        url_path = str(request.url.path).lower()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern.lower() in url_path:
                logger.warning(f"Suspicious pattern detected in URL: {pattern} from {request.client.host}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid request"}
                )
        
        # Check query parameters
        for key, value in request.query_params.items():
            value_str = str(value).lower()
            for pattern in self.SUSPICIOUS_PATTERNS:
                if pattern.lower() in value_str:
                    logger.warning(f"Suspicious pattern in query param: {pattern} from {request.client.host}")
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": "Invalid request parameters"}
                    )
        
        response = await call_next(request)
        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection for state-changing operations.
    Validates CSRF tokens for POST, PUT, PATCH, DELETE requests.
    """
    
    # Exempt paths (e.g., API endpoints with JWT auth)
    EXEMPT_PATHS = [
        "/auth/login",
        "/auth/register",
        "/auth/refresh",
        "/health",
        "/docs",
        "/openapi.json"
    ]
    
    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key
    
    def generate_csrf_token(self, session_id: str) -> str:
        """Generate CSRF token for a session."""
        timestamp = str(int(time.time()))
        data = f"{session_id}:{timestamp}:{self.secret_key}"
        token = hashlib.sha256(data.encode()).hexdigest()
        return f"{timestamp}:{token}"
    
    def validate_csrf_token(self, token: str, session_id: str, max_age: int = 3600) -> bool:
        """Validate CSRF token."""
        try:
            timestamp_str, token_hash = token.split(":", 1)
            timestamp = int(timestamp_str)
            
            # Check age
            if time.time() - timestamp > max_age:
                return False
            
            # Regenerate and compare
            expected_data = f"{session_id}:{timestamp_str}:{self.secret_key}"
            expected_hash = hashlib.sha256(expected_data.encode()).hexdigest()
            
            return secrets.compare_digest(token_hash, expected_hash)
        except Exception:
            return False
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip for safe methods and exempt paths
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return await call_next(request)
        
        if any(request.url.path.startswith(path) for path in self.EXEMPT_PATHS):
            return await call_next(request)
        
        # For API endpoints with JWT, skip CSRF (JWT provides protection)
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            return await call_next(request)
        
        # Validate CSRF token for form submissions
        csrf_token = request.headers.get("X-CSRF-Token") or request.cookies.get("csrf_token")
        session_id = request.cookies.get("session_id", "")
        
        if not csrf_token or not self.validate_csrf_token(csrf_token, session_id):
            logger.warning(f"CSRF validation failed from {request.client.host}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF validation failed"}
            )
        
        return await call_next(request)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Log security-relevant events for audit trail.
    """
    
    SENSITIVE_ENDPOINTS = [
        "/auth/login",
        "/auth/register",
        "/auction/bid",
        "/admin/",
        "/teams/",
        "/players/"
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()
        
        # Check if this is a sensitive endpoint
        is_sensitive = any(request.url.path.startswith(path) for path in self.SENSITIVE_ENDPOINTS)
        
        if is_sensitive:
            # Log request
            logger.info(
                f"AUDIT: {request.method} {request.url.path} "
                f"from {request.client.host} "
                f"user-agent: {request.headers.get('user-agent', 'unknown')}"
            )
        
        response = await call_next(request)
        
        if is_sensitive:
            duration = time.time() - start_time
            # Log response
            logger.info(
                f"AUDIT: {request.method} {request.url.path} "
                f"status={response.status_code} duration={duration:.3f}s"
            )
        
        return response


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Optional IP whitelist for admin endpoints.
    Can be enabled in production for extra security.
    """
    
    def __init__(self, app, whitelist: list = None, enabled: bool = False):
        super().__init__(app)
        self.whitelist = set(whitelist or [])
        self.enabled = enabled
    
    async def dispatch(self, request: Request, call_next: Callable):
        if not self.enabled:
            return await call_next(request)
        
        # Only check admin endpoints
        if not request.url.path.startswith("/admin/"):
            return await call_next(request)
        
        client_ip = request.client.host
        
        # Check forwarded headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        
        if client_ip not in self.whitelist:
            logger.warning(f"IP {client_ip} blocked from accessing admin endpoint")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"}
            )
        
        return await call_next(request)
