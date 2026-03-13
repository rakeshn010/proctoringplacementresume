"""
Integrated Security Middleware
Combines security monitoring, auto-blocking, and threat detection.
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging

from core.security_monitor import security_monitor
from core.auto_blocker import auto_blocker

logger = logging.getLogger(__name__)


class IntegratedSecurityMiddleware(BaseHTTPMiddleware):
    """
    Integrated security middleware that:
    1. Checks if IP is blocked
    2. Monitors for security threats
    3. Auto-blocks malicious IPs
    4. Logs security events
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # 1. Check if IP is blocked
        if auto_blocker.is_blocked(client_ip):
            block_info = auto_blocker.get_block_info(client_ip)
            logger.warning(f"🚫 Blocked IP attempted access: {client_ip}")
            
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Access denied. Your IP has been blocked due to security violations.",
                    "reason": block_info["reason"] if block_info else "Security violation",
                    "expires_at": block_info["expires_at"].isoformat() if block_info else None
                }
            )
        
        # 2. Check for path traversal attempts
        if security_monitor.detect_path_traversal(client_ip, str(request.url.path)):
            # Auto-block immediately
            auto_blocker.block_ip(
                ip=client_ip,
                reason="Path traversal attempt detected",
                duration_hours=48,
                severity="critical"
            )
            
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"}
            )
        
        # 3. Check request body for SQL injection and XSS (for POST/PUT/PATCH)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Get request body as string for scanning
                body = await request.body()
                body_str = body.decode('utf-8', errors='ignore')
                
                # Check for SQL injection
                if security_monitor.detect_sql_injection(
                    client_ip,
                    body_str,
                    str(request.url.path)
                ):
                    # Auto-block immediately
                    auto_blocker.block_ip(
                        ip=client_ip,
                        reason="SQL injection attempt detected",
                        duration_hours=72,
                        severity="critical"
                    )
                    
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Access denied"}
                    )
                
                # Check for XSS
                if security_monitor.detect_xss_attempt(
                    client_ip,
                    body_str,
                    str(request.url.path)
                ):
                    # Check if should auto-block
                    if security_monitor.should_block_ip(client_ip):
                        auto_blocker.block_ip(
                            ip=client_ip,
                            reason="Multiple XSS attempts detected",
                            duration_hours=24,
                            severity="high"
                        )
                    
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Access denied"}
                    )
                
                # Restore body for downstream handlers
                async def receive():
                    return {"type": "http.request", "body": body}
                
                request._receive = receive
                
            except Exception as e:
                logger.error(f"Error scanning request body: {e}")
        
        # 4. Process request
        response = await call_next(request)
        
        # 5. Check if this was a failed login (status 401 on /auth/login)
        if (response.status_code == 401 and 
            request.url.path.startswith("/auth/login")):
            
            # Record failed login
            should_block = security_monitor.record_failed_login(
                client_ip,
                "unknown"  # Email not available here
            )
            
            # Auto-block if too many attempts
            if should_block:
                auto_blocker.block_ip(
                    ip=client_ip,
                    reason="Brute force attack detected (5+ failed logins)",
                    duration_hours=1,
                    severity="high"
                )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded IP (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client
        return request.client.host if request.client else "unknown"


class SecurityEventLogger(BaseHTTPMiddleware):
    """
    Log security-relevant requests for audit trail.
    """
    
    SENSITIVE_ENDPOINTS = [
        "/auth/login",
        "/auth/register",
        "/auction/bid",
        "/admin/",
        "/api/security/"
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Check if this is a sensitive endpoint
        is_sensitive = any(
            request.url.path.startswith(path) 
            for path in self.SENSITIVE_ENDPOINTS
        )
        
        if is_sensitive:
            client_ip = self._get_client_ip(request)
            
            # Log request
            logger.info(
                f"🔒 Security-sensitive request: "
                f"{request.method} {request.url.path} "
                f"from {client_ip}"
            )
        
        response = await call_next(request)
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
