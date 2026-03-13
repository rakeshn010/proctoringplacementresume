"""
Automatic IP Blocking System
Blocks malicious IPs based on security violations.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
import logging

from database import db

logger = logging.getLogger(__name__)


class AutoBlocker:
    """
    Automatic IP blocking system.
    Blocks IPs after repeated security violations.
    """
    
    def __init__(self):
        self.blocked_ips = set()
        self.load_blocked_ips()
    
    def load_blocked_ips(self):
        """Load currently blocked IPs from database."""
        try:
            blocked = db.blocked_ips.find({
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            })
            
            for block in blocked:
                self.blocked_ips.add(block["ip"])
            
            logger.info(f"Loaded {len(self.blocked_ips)} blocked IPs")
        except Exception as e:
            logger.error(f"Error loading blocked IPs: {e}")
    
    def block_ip(
        self,
        ip: str,
        reason: str,
        duration_hours: int = 24,
        severity: str = "high"
    ):
        """
        Block an IP address.
        
        Args:
            ip: IP address to block
            reason: Reason for blocking
            duration_hours: How long to block (default 24 hours)
            severity: Severity level (low, medium, high, critical)
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=duration_hours)
        
        # Add to memory
        self.blocked_ips.add(ip)
        
        # Add to database
        try:
            db.blocked_ips.insert_one({
                "ip": ip,
                "reason": reason,
                "severity": severity,
                "blocked_at": now,
                "expires_at": expires_at,
                "duration_hours": duration_hours
            })
            
            logger.warning(
                f"🚫 BLOCKED IP: {ip}\n"
                f"Reason: {reason}\n"
                f"Duration: {duration_hours} hours\n"
                f"Expires: {expires_at}"
            )
        except Exception as e:
            logger.error(f"Error blocking IP {ip}: {e}")
    
    def is_blocked(self, ip: str) -> bool:
        """
        Check if IP is currently blocked.
        
        Args:
            ip: IP address to check
        
        Returns:
            True if blocked, False otherwise
        """
        # Check memory first (fast)
        if ip in self.blocked_ips:
            return True
        
        # Check database (slower but authoritative)
        try:
            block = db.blocked_ips.find_one({
                "ip": ip,
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            })
            
            if block:
                # Add to memory for faster future checks
                self.blocked_ips.add(ip)
                return True
        except Exception as e:
            logger.error(f"Error checking blocked IP {ip}: {e}")
        
        return False
    
    def unblock_ip(self, ip: str):
        """
        Manually unblock an IP address.
        
        Args:
            ip: IP address to unblock
        """
        # Remove from memory
        self.blocked_ips.discard(ip)
        
        # Remove from database
        try:
            result = db.blocked_ips.delete_many({"ip": ip})
            logger.info(f"Unblocked IP {ip} ({result.deleted_count} records removed)")
        except Exception as e:
            logger.error(f"Error unblocking IP {ip}: {e}")
    
    def get_block_info(self, ip: str) -> Optional[Dict]:
        """
        Get information about a blocked IP.
        
        Args:
            ip: IP address to check
        
        Returns:
            Block information dict or None
        """
        try:
            block = db.blocked_ips.find_one({
                "ip": ip,
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            })
            
            if block:
                return {
                    "ip": block["ip"],
                    "reason": block["reason"],
                    "severity": block["severity"],
                    "blocked_at": block["blocked_at"],
                    "expires_at": block["expires_at"],
                    "duration_hours": block["duration_hours"]
                }
        except Exception as e:
            logger.error(f"Error getting block info for {ip}: {e}")
        
        return None
    
    def get_blocked_ips(self) -> List[Dict]:
        """
        Get all currently blocked IPs.
        
        Returns:
            List of blocked IP information
        """
        try:
            blocks = db.blocked_ips.find({
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            }).sort("blocked_at", -1)
            
            return [{
                "ip": block["ip"],
                "reason": block["reason"],
                "severity": block["severity"],
                "blocked_at": block["blocked_at"],
                "expires_at": block["expires_at"],
                "duration_hours": block["duration_hours"]
            } for block in blocks]
        except Exception as e:
            logger.error(f"Error getting blocked IPs: {e}")
            return []
    
    def cleanup_expired_blocks(self):
        """Remove expired IP blocks from database."""
        try:
            result = db.blocked_ips.delete_many({
                "expires_at": {"$lt": datetime.now(timezone.utc)}
            })
            
            if result.deleted_count > 0:
                logger.info(f"Cleaned up {result.deleted_count} expired IP blocks")
                # Reload blocked IPs
                self.blocked_ips.clear()
                self.load_blocked_ips()
            
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up expired blocks: {e}")
            return 0
    
    def get_stats(self) -> Dict:
        """Get blocking statistics."""
        try:
            total_blocks = db.blocked_ips.count_documents({})
            active_blocks = db.blocked_ips.count_documents({
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            })
            
            # Count by severity
            severity_counts = {}
            for severity in ["low", "medium", "high", "critical"]:
                count = db.blocked_ips.count_documents({
                    "severity": severity,
                    "expires_at": {"$gt": datetime.now(timezone.utc)}
                })
                severity_counts[severity] = count
            
            return {
                "total_blocks_all_time": total_blocks,
                "active_blocks": active_blocks,
                "blocks_by_severity": severity_counts,
                "memory_cache_size": len(self.blocked_ips)
            }
        except Exception as e:
            logger.error(f"Error getting blocker stats: {e}")
            return {
                "error": str(e),
                "active_blocks": len(self.blocked_ips)
            }


# Global auto blocker instance
auto_blocker = AutoBlocker()
