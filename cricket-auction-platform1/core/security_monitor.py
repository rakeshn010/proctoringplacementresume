"""
Real-time Security Monitoring and Threat Detection
Tracks security events, detects attacks, and sends alerts.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import logging
from collections import defaultdict

from database import db

logger = logging.getLogger(__name__)


class SecurityMonitor:
    """
    Real-time security monitoring system.
    Detects and logs security threats.
    """
    
    def __init__(self):
        self.failed_login_attempts = defaultdict(list)  # {ip: [timestamps]}
        self.suspicious_ips = set()
        self.blocked_ips = set()
        self.ip_violations = defaultdict(int)  # {ip: count}
        
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        ip: str,
        details: dict
    ):
        """
        Log security event to database.
        
        Args:
            event_type: Type of event (brute_force, sql_injection, etc.)
            severity: low, medium, high, critical
            ip: IP address of attacker
            details: Additional event details
        """
        event = {
            "timestamp": datetime.now(timezone.utc),
            "type": event_type,
            "severity": severity,
            "ip": ip,
            "details": details
        }
        
        try:
            db.security_events.insert_one(event)
            logger.info(f"Security event logged: {event_type} from {ip} (severity: {severity})")
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
        
        # Send alert if critical
        if severity == "critical":
            self.send_alert(event)
    
    def record_failed_login(self, ip: str, email: str):
        """Record failed login attempt."""
        now = datetime.now(timezone.utc)
        self.failed_login_attempts[ip].append(now)
        
        # Clean old attempts (older than 15 minutes)
        cutoff = now - timedelta(minutes=15)
        self.failed_login_attempts[ip] = [
            ts for ts in self.failed_login_attempts[ip] if ts > cutoff
        ]
        
        # Check for brute force
        attempts = len(self.failed_login_attempts[ip])
        if attempts >= 5:
            self.detect_brute_force(ip, attempts, email)
            return True  # Should block
        
        return False
    
    def detect_brute_force(self, ip: str, failed_attempts: int, email: str):
        """Detect brute force attacks."""
        self.log_security_event(
            event_type="brute_force_detected",
            severity="high",
            ip=ip,
            details={
                "failed_attempts": failed_attempts,
                "target_email": email,
                "time_window": "15 minutes"
            }
        )
        
        self.suspicious_ips.add(ip)
        self.ip_violations[ip] += 1
        
        logger.warning(f"🚨 Brute force detected from {ip}: {failed_attempts} failed attempts")
    
    def detect_sql_injection(self, ip: str, request_data: str, endpoint: str) -> bool:
        """Detect SQL injection attempts."""
        sql_patterns = [
            "UNION SELECT", "DROP TABLE", "'; --", "OR 1=1",
            "EXEC(", "xp_cmdshell", "INSERT INTO", "DELETE FROM",
            "UPDATE SET", "CREATE TABLE", "ALTER TABLE"
        ]
        
        data_lower = request_data.lower()
        for pattern in sql_patterns:
            if pattern.lower() in data_lower:
                self.log_security_event(
                    event_type="sql_injection_attempt",
                    severity="critical",
                    ip=ip,
                    details={
                        "pattern": pattern,
                        "endpoint": endpoint,
                        "data_sample": request_data[:200]
                    }
                )
                
                self.ip_violations[ip] += 3  # Severe violation
                logger.critical(f"🚨 SQL injection attempt from {ip}: pattern '{pattern}'")
                return True
        
        return False
    
    def detect_xss_attempt(self, ip: str, request_data: str, endpoint: str) -> bool:
        """Detect XSS attempts."""
        xss_patterns = [
            "<script", "javascript:", "onerror=", "onload=",
            "onclick=", "onmouseover=", "<iframe", "eval(",
            "document.cookie", "window.location"
        ]
        
        data_lower = request_data.lower()
        for pattern in xss_patterns:
            if pattern.lower() in data_lower:
                self.log_security_event(
                    event_type="xss_attempt",
                    severity="high",
                    ip=ip,
                    details={
                        "pattern": pattern,
                        "endpoint": endpoint,
                        "data_sample": request_data[:200]
                    }
                )
                
                self.ip_violations[ip] += 2
                logger.warning(f"🚨 XSS attempt from {ip}: pattern '{pattern}'")
                return True
        
        return False
    
    def detect_path_traversal(self, ip: str, path: str) -> bool:
        """Detect path traversal attempts."""
        traversal_patterns = [
            "../", "..\\", "etc/passwd", "etc\\passwd",
            "windows\\system32", "/etc/shadow", "cmd.exe"
        ]
        
        path_lower = path.lower()
        for pattern in traversal_patterns:
            if pattern.lower() in path_lower:
                self.log_security_event(
                    event_type="path_traversal_attempt",
                    severity="critical",
                    ip=ip,
                    details={
                        "pattern": pattern,
                        "path": path
                    }
                )
                
                self.ip_violations[ip] += 3
                logger.critical(f"🚨 Path traversal attempt from {ip}: {pattern}")
                return True
        
        return False
    
    def should_block_ip(self, ip: str) -> bool:
        """Check if IP should be blocked based on violations."""
        return self.ip_violations[ip] >= 3
    
    def is_suspicious_ip(self, ip: str) -> bool:
        """Check if IP is marked as suspicious."""
        return ip in self.suspicious_ips
    
    def get_failed_login_count(self, ip: str) -> int:
        """Get failed login count for IP."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=15)
        
        # Clean old attempts
        self.failed_login_attempts[ip] = [
            ts for ts in self.failed_login_attempts[ip] if ts > cutoff
        ]
        
        return len(self.failed_login_attempts[ip])
    
    def send_alert(self, event: dict):
        """
        Send alert to admin.
        Can be extended to send emails, Slack messages, etc.
        """
        logger.critical(
            f"🚨 SECURITY ALERT 🚨\n"
            f"Type: {event['type']}\n"
            f"Severity: {event['severity']}\n"
            f"IP: {event['ip']}\n"
            f"Details: {event['details']}"
        )
        
        # TODO: Implement email/Slack notifications
        # send_email(admin_email, subject, body)
        # send_slack_message(webhook_url, message)
    
    def get_security_stats(self) -> Dict:
        """Get security statistics for dashboard."""
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        
        try:
            # Get events from last 24 hours
            recent_events = list(db.security_events.find({
                "timestamp": {"$gte": last_24h}
            }))
            
            # Count by type
            events_by_type = defaultdict(int)
            events_by_severity = defaultdict(int)
            
            for event in recent_events:
                events_by_type[event["type"]] += 1
                events_by_severity[event["severity"]] += 1
            
            # Get top attacking IPs
            ip_counts = defaultdict(int)
            for event in recent_events:
                ip_counts[event["ip"]] += 1
            
            top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "total_events_24h": len(recent_events),
                "events_by_type": dict(events_by_type),
                "events_by_severity": dict(events_by_severity),
                "top_attacking_ips": [{"ip": ip, "count": count} for ip, count in top_ips],
                "suspicious_ips_count": len(self.suspicious_ips),
                "blocked_ips_count": len(self.blocked_ips),
                "active_violations": dict(self.ip_violations)
            }
        except Exception as e:
            logger.error(f"Error getting security stats: {e}")
            return {
                "error": str(e),
                "total_events_24h": 0
            }
    
    def cleanup_old_events(self, days: int = 90):
        """Clean up old security events (data retention)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        try:
            result = db.security_events.delete_many({
                "timestamp": {"$lt": cutoff}
            })
            logger.info(f"Cleaned up {result.deleted_count} old security events")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up security events: {e}")
            return 0


# Global security monitor instance
security_monitor = SecurityMonitor()
