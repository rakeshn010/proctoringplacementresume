"""
Application monitoring and metrics.
Provides health checks, metrics, and performance monitoring.
"""
from fastapi import APIRouter, Response
from datetime import datetime, timezone
import psutil
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Track application start time
APP_START_TIME = time.time()

router = APIRouter(tags=["Monitoring"])


def get_system_metrics() -> Dict[str, Any]:
    """Get system resource metrics."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "memory": {
                "total_mb": round(memory.total / (1024 * 1024), 2),
                "used_mb": round(memory.used / (1024 * 1024), 2),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
                "used_gb": round(disk.used / (1024 * 1024 * 1024), 2),
                "percent": disk.percent
            }
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return {}


def check_database_health() -> Dict[str, Any]:
    """Check database connection health."""
    try:
        from database import db
        
        # Simple ping
        db.command('ping')
        
        # Get collection counts
        users_count = db.users.count_documents({})
        players_count = db.players.count_documents({})
        teams_count = db.teams.count_documents({})
        
        return {
            "status": "healthy",
            "collections": {
                "users": users_count,
                "players": players_count,
                "teams": teams_count
            }
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_redis_health() -> Dict[str, Any]:
    """Check Redis connection health."""
    try:
        from core.redis_session import redis_session_manager
        
        if not redis_session_manager.redis_client:
            return {
                "status": "disabled",
                "message": "Redis not configured"
            }
        
        # Ping Redis
        redis_session_manager.redis_client.ping()
        
        # Get info
        info = redis_session_manager.redis_client.info()
        
        return {
            "status": "healthy",
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_mb": round(info.get("used_memory", 0) / (1024 * 1024), 2),
            "uptime_days": round(info.get("uptime_in_seconds", 0) / 86400, 2)
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def get_websocket_metrics() -> Dict[str, Any]:
    """Get WebSocket connection metrics."""
    try:
        from websocket.manager import manager
        
        return {
            "active_connections": len(manager.active_connections),
            "rooms": len(manager.rooms),
            "compression_enabled": manager.compression_enabled,
            "heartbeat_interval": manager.heartbeat_interval
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket metrics: {e}")
        return {}


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    Returns 200 if application is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with all system components.
    Use for monitoring and alerting.
    """
    uptime_seconds = time.time() - APP_START_TIME
    
    health_data = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(uptime_seconds, 2),
        "uptime_hours": round(uptime_seconds / 3600, 2),
        "components": {
            "database": check_database_health(),
            "redis": check_redis_health(),
            "websocket": get_websocket_metrics()
        },
        "system": get_system_metrics()
    }
    
    # Determine overall health
    db_healthy = health_data["components"]["database"]["status"] == "healthy"
    redis_status = health_data["components"]["redis"]["status"]
    redis_healthy = redis_status in ["healthy", "disabled"]
    
    if not (db_healthy and redis_healthy):
        health_data["status"] = "degraded"
    
    return health_data


@router.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus-compatible metrics endpoint.
    Returns metrics in Prometheus text format.
    """
    try:
        from core.redis_session import redis_session_manager
        from websocket.manager import manager
        from database import db
        
        # Collect metrics
        uptime = time.time() - APP_START_TIME
        system = get_system_metrics()
        
        # Active sessions
        active_sessions = redis_session_manager.get_active_session_count()
        
        # WebSocket connections
        ws_connections = len(manager.active_connections)
        
        # Database counts
        users_count = db.users.count_documents({})
        players_count = db.players.count_documents({})
        teams_count = db.teams.count_documents({})
        bids_count = db.bid_history.count_documents({})
        
        # Format as Prometheus metrics
        metrics = f"""# HELP app_uptime_seconds Application uptime in seconds
# TYPE app_uptime_seconds gauge
app_uptime_seconds {uptime}

# HELP app_active_sessions Number of active user sessions
# TYPE app_active_sessions gauge
app_active_sessions {active_sessions}

# HELP app_websocket_connections Number of active WebSocket connections
# TYPE app_websocket_connections gauge
app_websocket_connections {ws_connections}

# HELP app_users_total Total number of registered users
# TYPE app_users_total gauge
app_users_total {users_count}

# HELP app_players_total Total number of players
# TYPE app_players_total gauge
app_players_total {players_count}

# HELP app_teams_total Total number of teams
# TYPE app_teams_total gauge
app_teams_total {teams_count}

# HELP app_bids_total Total number of bids placed
# TYPE app_bids_total counter
app_bids_total {bids_count}

# HELP system_cpu_percent CPU usage percentage
# TYPE system_cpu_percent gauge
system_cpu_percent {system.get('cpu', {}).get('percent', 0)}

# HELP system_memory_percent Memory usage percentage
# TYPE system_memory_percent gauge
system_memory_percent {system.get('memory', {}).get('percent', 0)}

# HELP system_disk_percent Disk usage percentage
# TYPE system_disk_percent gauge
system_disk_percent {system.get('disk', {}).get('percent', 0)}
"""
        
        return Response(content=metrics, media_type="text/plain")
        
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return Response(
            content=f"# Error generating metrics: {e}",
            media_type="text/plain",
            status_code=500
        )


@router.get("/stats")
async def application_stats():
    """
    Application statistics for admin dashboard.
    Returns detailed stats about the application.
    """
    try:
        from database import db
        from core.redis_session import redis_session_manager
        from websocket.manager import manager
        
        # Database stats
        users_count = db.users.count_documents({})
        admin_count = db.users.count_documents({"is_admin": True})
        players_count = db.players.count_documents({})
        sold_players = db.players.count_documents({"status": "sold"})
        teams_count = db.teams.count_documents({})
        bids_count = db.bid_history.count_documents({})
        
        # Session stats
        active_sessions = redis_session_manager.get_active_session_count()
        
        # WebSocket stats
        ws_connections = len(manager.active_connections)
        ws_rooms = len(manager.rooms)
        
        # System stats
        uptime = time.time() - APP_START_TIME
        system = get_system_metrics()
        
        return {
            "ok": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime": {
                "seconds": round(uptime, 2),
                "hours": round(uptime / 3600, 2),
                "days": round(uptime / 86400, 2)
            },
            "database": {
                "users": users_count,
                "admins": admin_count,
                "players": players_count,
                "sold_players": sold_players,
                "teams": teams_count,
                "total_bids": bids_count
            },
            "sessions": {
                "active": active_sessions
            },
            "websocket": {
                "connections": ws_connections,
                "rooms": ws_rooms
            },
            "system": system
        }
        
    except Exception as e:
        logger.error(f"Error getting application stats: {e}")
        return {
            "ok": False,
            "error": str(e)
        }
