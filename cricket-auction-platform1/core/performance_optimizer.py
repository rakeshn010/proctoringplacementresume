"""
Performance Optimization Middleware
Professional-grade optimizations for real-time applications
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers, MutableHeaders
import time
import hashlib
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Advanced performance optimization middleware
    - Response time tracking
    - ETag generation for caching
    - Preload hints for critical resources
    - Connection keep-alive optimization
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Track response time
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
        
        # Add performance headers
        self._add_performance_headers(response, request)
        
        # Log slow requests
        if process_time > 1.0:
            logger.warning(f"Slow request: {request.url.path} took {process_time:.2f}s")
        
        return response
    
    def _add_performance_headers(self, response: Response, request: Request):
        """Add performance optimization headers"""
        
        # Connection optimization
        response.headers["Connection"] = "keep-alive"
        response.headers["Keep-Alive"] = "timeout=5, max=100"
        
        # DNS prefetch for external resources
        if request.url.path in ["/", "/team/dashboard", "/admin", "/live"]:
            response.headers["X-DNS-Prefetch-Control"] = "on"


class ETaggerMiddleware(BaseHTTPMiddleware):
    """
    ETag generation for efficient caching
    Reduces bandwidth and improves load times
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if client sent If-None-Match header
        client_etag = request.headers.get("if-none-match")
        
        # Get response
        response = await call_next(request)
        
        # Only add ETag for GET requests and successful responses
        if request.method == "GET" and response.status_code == 200:
            # Generate ETag from response body
            if hasattr(response, "body"):
                body = response.body
                etag = self._generate_etag(body)
                response.headers["ETag"] = etag
                
                # Check if client has cached version
                if client_etag == etag:
                    return Response(status_code=304, headers=dict(response.headers))
        
        return response
    
    def _generate_etag(self, content: bytes) -> str:
        """Generate ETag from content"""
        return f'"{hashlib.md5(content).hexdigest()}"'


class ResponseCompressionOptimizer(BaseHTTPMiddleware):
    """
    Optimize compression settings based on content type
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add Vary header for proper caching with compression
        if "Content-Encoding" in response.headers:
            response.headers["Vary"] = "Accept-Encoding"
        
        # Suggest compression for compressible content
        content_type = response.headers.get("content-type", "")
        if any(ct in content_type for ct in ["text/", "application/json", "application/javascript"]):
            # Already handled by GZipMiddleware, just ensure proper headers
            pass
        
        return response


class StaticAssetOptimizer(BaseHTTPMiddleware):
    """
    Optimize static asset delivery
    - Long-term caching for versioned assets
    - Immutable flag for fingerprinted files
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        path = request.url.path
        
        # Long-term caching for versioned static files
        if path.startswith("/static/"):
            # Check if file has version query parameter
            if "v=" in str(request.url.query):
                # Versioned files can be cached for 1 year
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            else:
                # Non-versioned files: short cache with revalidation
                response.headers["Cache-Control"] = "public, max-age=3600, must-revalidate"
            
            # Add CORS for static assets (for CDN compatibility)
            response.headers["Access-Control-Allow-Origin"] = "*"
            
            # Add timing headers
            response.headers["Timing-Allow-Origin"] = "*"
        
        return response


class DatabaseQueryOptimizer:
    """
    Helper class for database query optimization
    """
    
    @staticmethod
    def get_projection_fields(fields: list) -> dict:
        """
        Create MongoDB projection to fetch only needed fields
        Reduces data transfer and improves query speed
        """
        return {field: 1 for field in fields}
    
    @staticmethod
    def create_compound_index(collection, fields: list, unique: bool = False):
        """
        Create compound index for faster queries
        """
        index_spec = [(field, 1) for field in fields]
        collection.create_index(index_spec, unique=unique)
        logger.info(f"Created compound index on {collection.name}: {fields}")
    
    @staticmethod
    def add_query_hint(query: dict, index_name: str) -> dict:
        """
        Add hint to use specific index
        """
        return {"$query": query, "$hint": index_name}


# Export optimizers
__all__ = [
    'PerformanceMiddleware',
    'ETaggerMiddleware', 
    'ResponseCompressionOptimizer',
    'StaticAssetOptimizer',
    'DatabaseQueryOptimizer'
]
