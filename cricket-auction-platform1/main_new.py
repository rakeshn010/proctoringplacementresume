"""
Cricket Auction Platform - Main Application
Production-ready FastAPI application with WebSocket support.
Enhanced with security middleware and rate limiting.
Updated: 2026-02-16 - Added security enhancements and performance improvements
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse
import logging
from contextlib import asynccontextmanager

from core.config import settings
from core.security_middleware import (
    SecurityHeadersMiddleware,
    RequestValidationMiddleware,
    AuditLogMiddleware,
    IPWhitelistMiddleware
)
from core.auth_middleware import StrictAuthMiddleware
from core.rate_limiter import rate_limiter
from core.integrated_security import IntegratedSecurityMiddleware, SecurityEventLogger
from core.security_monitor import security_monitor
from core.auto_blocker import auto_blocker
from core.log_sanitizer import setup_sanitized_logging
from core.performance_optimizer import (
    PerformanceMiddleware,
    ETaggerMiddleware,
    ResponseCompressionOptimizer,
    StaticAssetOptimizer
)
from routers import auth, players, teams, auction, admin, reports, viewer
from database import db


# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Setup PII sanitization for logs
    setup_sanitized_logging()
    logger.info("✅ PII sanitization enabled")
    
    # Start rate limiter cleanup
    if settings.ENABLE_RATE_LIMITING:
        rate_limiter.start_cleanup()
        logger.info("Rate limiter started")
    
    # Start session cleanup
    from core.session_manager import session_manager
    from core.cloudinary_config import is_cloudinary_configured
    import asyncio
    
    # Check Cloudinary configuration
    is_cloudinary_configured()
    
    async def cleanup_sessions():
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            session_manager.cleanup_expired_sessions()
    
    asyncio.create_task(cleanup_sessions())
    logger.info("Session manager started")
    
    # Start security monitoring cleanup
    async def cleanup_security():
        while True:
            await asyncio.sleep(3600)  # Every hour
            security_monitor.cleanup_old_events(days=90)
            auto_blocker.cleanup_expired_blocks()
    
    asyncio.create_task(cleanup_security())
    logger.info("✅ Security monitoring started")
    logger.info(f"✅ Auto-blocker initialized with {len(auto_blocker.blocked_ips)} blocked IPs")
    
    # Create indexes
    try:
        db.users.create_index("email", unique=True)
        db.bid_history.create_index([("player_id", 1), ("timestamp", -1)])
        db.bid_history.create_index([("team_id", 1)])
        db.players.create_index("role")
        db.players.create_index("category")
        db.players.create_index("status")
        db.players.create_index("auction_round")
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
    
    # Run simple database migration for new fields
    try:
        logger.info("Running database migration...")
        
        # Update players with missing fields
        result = db.players.update_many(
            {"role": {"$exists": False}},
            {"$set": {"role": None}}
        )
        if result.modified_count > 0:
            logger.info(f"Added 'role' field to {result.modified_count} players")
        
        result = db.players.update_many(
            {"image_path": {"$exists": False}},
            {"$set": {"image_path": None}}
        )
        if result.modified_count > 0:
            logger.info(f"Added 'image_path' field to {result.modified_count} players")
        
        result = db.players.update_many(
            {"auction_round": {"$exists": False}},
            {"$set": {"auction_round": 1}}
        )
        if result.modified_count > 0:
            logger.info(f"Added 'auction_round' field to {result.modified_count} players")
        
        # Update auction config
        config = db.config.find_one({"key": "auction"})
        if config and "auction_round" not in config:
            db.config.update_one(
                {"key": "auction"},
                {"$set": {"auction_round": 1}}
            )
            logger.info("Added 'auction_round' to auction config")
        
        logger.info("Database migration completed")
    except Exception as e:
        logger.warning(f"Migration warning: {e}")
    
    logger.info("✅ Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-ready Cricket Auction Platform with real-time bidding and enhanced security",
    lifespan=lifespan
)


# Add Middleware (order matters!)
# 0. HTTPS redirect middleware (FIRST - to handle Railway proxy)
@app.middleware("http")
async def https_redirect_middleware(request: Request, call_next):
    """Ensure redirects use HTTPS when behind a proxy."""
    # Check if we're behind a proxy (Railway sets X-Forwarded-Proto)
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if forwarded_proto == "https":
        # Override the request URL scheme to HTTPS
        request.scope["scheme"] = "https"
    response = await call_next(request)
    return response

# 1. Performance tracking (FIRST - to measure total time)
app.add_middleware(PerformanceMiddleware)

# 2. Integrated Security (IP blocking, threat detection)
app.add_middleware(IntegratedSecurityMiddleware)
logger.info("✅ Integrated security middleware enabled")

# 3. Security event logging
app.add_middleware(SecurityEventLogger)

# 4. Strict Authentication
app.add_middleware(StrictAuthMiddleware)

# 5. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 6. Request validation
app.add_middleware(RequestValidationMiddleware)

# 7. Audit logging
app.add_middleware(AuditLogMiddleware)

# 8. IP whitelist (if enabled)
if settings.ENABLE_IP_WHITELIST:
    app.add_middleware(
        IPWhitelistMiddleware,
        whitelist=settings.admin_ip_whitelist_list,
        enabled=True
    )
    logger.info(f"IP whitelist enabled for admin endpoints: {settings.admin_ip_whitelist_list}")

# 9. CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 10. ETag for caching
app.add_middleware(ETaggerMiddleware)

# 11. Static asset optimization
app.add_middleware(StaticAssetOptimizer)

# 12. Response compression optimization
app.add_middleware(ResponseCompressionOptimizer)

# 13. Response compression (LAST)
if settings.ENABLE_RESPONSE_COMPRESSION:
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    logger.info("Response compression enabled")


# Add cache control middleware for static files
@app.middleware("http")
async def add_cache_control_headers(request: Request, call_next):
    """Add cache control headers to prevent aggressive caching of JS/CSS files."""
    response = await call_next(request)
    
    # For JavaScript and CSS files, use short cache with revalidation
    if request.url.path.startswith("/static/") and (
        request.url.path.endswith(".js") or 
        request.url.path.endswith(".css")
    ):
        response.headers["Cache-Control"] = "public, max-age=300, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    
    return response


# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "csp_updated": "2026-02-18-v2"  # Version marker
    }


# Debug endpoint to check authentication
@app.get("/debug/auth")
async def debug_auth(request: Request):
    """Debug endpoint to check authentication status."""
    return {
        "cookies": dict(request.cookies),
        "is_authenticated": getattr(request.state, "is_authenticated", False),
        "user_role": getattr(request.state, "user_role", None),
        "user_email": getattr(request.state, "user_email", None),
        "user_id": getattr(request.state, "user_id", None),
    }


# Service Worker endpoint (must be at root for proper scope)
@app.get("/service-worker.js")
async def serve_service_worker():
    """Serve the service worker with proper headers."""
    from fastapi.responses import FileResponse
    response = FileResponse("static/service-worker.js", media_type="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


# Root endpoint - Player Registration Page
@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Serve the main player registration page."""
    return templates.TemplateResponse("index.html", {"request": request})


# Hollywood Cinematic Live Auction Studio
@app.get("/live", response_class=HTMLResponse)
async def live_cinematic_studio(request: Request):
    """Serve the Level 3 Hollywood cinematic live auction studio."""
    return templates.TemplateResponse("live_studio.html", {"request": request})


# Admin page
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Serve the admin dashboard page."""
    return templates.TemplateResponse("admin_fresh.html", {"request": request})


# Debug admin page - DISABLED (file not found)
# @app.get("/debug_admin.html", response_class=HTMLResponse)
# async def debug_admin_page(request: Request):
#     """Serve the debug admin page."""
#     with open("debug_admin.html", "r", encoding="utf-8") as f:
#         return HTMLResponse(content=f.read())


# Team dashboard page
@app.get("/team/dashboard", response_class=HTMLResponse)
async def team_dashboard_page(request: Request):
    """Serve the advanced team dashboard page."""
    return templates.TemplateResponse("team_dashboard_new.html", {"request": request})
    return templates.TemplateResponse("team_dashboard.html", {"request": request})


# User dashboard page
@app.get("/user/dashboard", response_class=HTMLResponse)
async def user_dashboard_page(request: Request):
    """Serve the user dashboard page with action options."""
    return templates.TemplateResponse("user_dashboard.html", {"request": request})


# Include routers
app.include_router(auth.router)
app.include_router(players.router)
app.include_router(teams.router)
app.include_router(auction.router)
app.include_router(admin.router)
app.include_router(reports.router)
app.include_router(viewer.router)

# Include new feature routers
from routers import chat, wishlist, comparison
app.include_router(chat.router)
app.include_router(wishlist.router)
app.include_router(comparison.router)

# Include monitoring router
from core.monitoring import router as monitoring_router
app.include_router(monitoring_router)

# Include NEW enhancement routers (2026-03-13)
from routers import ai, analytics, leaderboard
app.include_router(ai.router)
app.include_router(analytics.router)
app.include_router(leaderboard.router)


# Error handlers
from fastapi.responses import JSONResponse

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found", "status_code": 404}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler."""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status_code": 500}
    )


if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "main_new:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
