"""
Advanced rate limiting for API endpoints.
Prevents abuse and ensures fair usage.
"""
from typing import Dict, Optional
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Request, status
from collections import defaultdict
import asyncio


class RateLimiter:
    """
    Token bucket rate limiter with sliding window.
    Provides per-user and per-IP rate limiting.
    """
    
    def __init__(self):
        # User-based rate limits: {user_id: [(timestamp, count)]}
        self.user_requests: Dict[str, list] = defaultdict(list)
        # IP-based rate limits: {ip: [(timestamp, count)]}
        self.ip_requests: Dict[str, list] = defaultdict(list)
        # Bid rate limits (stricter): {user_id: [timestamps]}
        self.bid_requests: Dict[str, list] = defaultdict(list)
        # Cleanup task
        self.cleanup_task = None
        
    async def check_rate_limit(
        self,
        identifier: str,
        limit: int = 100,
        window_seconds: int = 60,
        limit_type: str = "general"
    ) -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: User ID or IP address
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            limit_type: Type of limit (general, bid, auth)
        
        Returns:
            True if within limit, raises HTTPException otherwise
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Select appropriate storage
        if limit_type == "bid":
            requests = self.bid_requests[identifier]
        elif limit_type == "ip":
            requests = self.ip_requests[identifier]
        else:
            requests = self.user_requests[identifier]
        
        # Remove old requests
        requests[:] = [ts for ts in requests if ts > cutoff]
        
        # Check limit
        if len(requests) >= limit:
            retry_after = int((requests[0] - cutoff).total_seconds()) + 1
            
            # More user-friendly error message
            if limit_type == "ip":
                detail = f"Too many login attempts. Please wait {retry_after} seconds before trying again."
            elif limit_type == "bid":
                detail = f"Too many bids. Please wait {retry_after} seconds before bidding again."
            else:
                detail = f"Rate limit exceeded. Please wait {retry_after} seconds."
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail,
                headers={"Retry-After": str(retry_after)}
            )
        
        # Add current request
        requests.append(now)
        return True
    
    async def check_bid_rate_limit(self, user_id: str) -> bool:
        """
        Stricter rate limit for bidding (prevents spam).
        Max 10 bids per minute per user.
        """
        return await self.check_rate_limit(
            identifier=user_id,
            limit=10,
            window_seconds=60,
            limit_type="bid"
        )
    
    async def check_auth_rate_limit(self, ip: str) -> bool:
        """
        Rate limit for authentication attempts (prevents brute force).
        Max 10 attempts per 5 minutes per IP (increased for development).
        """
        return await self.check_rate_limit(
            identifier=ip,
            limit=10,  # Increased from 5 to 10
            window_seconds=300,
            limit_type="ip"
        )
    
    async def check_api_rate_limit(self, user_id: str) -> bool:
        """
        General API rate limit.
        Max 100 requests per minute per user.
        """
        return await self.check_rate_limit(
            identifier=user_id,
            limit=100,
            window_seconds=60,
            limit_type="general"
        )
    
    async def cleanup_old_entries(self):
        """Periodically clean up old rate limit entries."""
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=10)
            
            # Clean user requests
            for user_id in list(self.user_requests.keys()):
                self.user_requests[user_id] = [
                    ts for ts in self.user_requests[user_id] if ts > cutoff
                ]
                if not self.user_requests[user_id]:
                    del self.user_requests[user_id]
            
            # Clean IP requests
            for ip in list(self.ip_requests.keys()):
                self.ip_requests[ip] = [
                    ts for ts in self.ip_requests[ip] if ts > cutoff
                ]
                if not self.ip_requests[ip]:
                    del self.ip_requests[ip]
            
            # Clean bid requests
            for user_id in list(self.bid_requests.keys()):
                self.bid_requests[user_id] = [
                    ts for ts in self.bid_requests[user_id] if ts > cutoff
                ]
                if not self.bid_requests[user_id]:
                    del self.bid_requests[user_id]
    
    def start_cleanup(self):
        """Start the cleanup background task."""
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self.cleanup_old_entries())
    
    def get_stats(self) -> Dict:
        """Get current rate limiter statistics."""
        return {
            "active_users": len(self.user_requests),
            "active_ips": len(self.ip_requests),
            "active_bidders": len(self.bid_requests),
            "total_tracked_requests": sum(len(v) for v in self.user_requests.values())
        }
    
    def clear_ip_limits(self, ip: str):
        """Clear rate limits for a specific IP (admin function)."""
        if ip in self.ip_requests:
            del self.ip_requests[ip]
            logger.info(f"Cleared rate limits for IP: {ip}")
    
    def clear_all_limits(self):
        """Clear all rate limits (admin function)."""
        self.user_requests.clear()
        self.ip_requests.clear()
        self.bid_requests.clear()
        logger.info("Cleared all rate limits")


# Global rate limiter instance
rate_limiter = RateLimiter()


async def get_client_ip(request: Request) -> str:
    """Extract client IP from request, considering proxies."""
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
