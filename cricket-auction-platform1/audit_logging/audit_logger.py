"""
Audit logging system for tracking all important events.
Stores comprehensive audit trail in MongoDB.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging

from database import db

logger = logging.getLogger(__name__)


class AuditLogger:
    """Comprehensive audit logging system."""
    
    @staticmethod
    def log_bid(
        player_id: str,
        player_name: str,
        team_id: str,
        team_name: str,
        bidder_id: str,
        bidder_email: str,
        bid_amount: float,
        is_winning: bool
    ):
        """
        Log a bid event.
        
        Args:
            player_id: Player ID
            player_name: Player name
            team_id: Team ID
            team_name: Team name
            bidder_id: Bidder user ID
            bidder_email: Bidder email
            bid_amount: Bid amount
            is_winning: Whether this is the winning bid
        """
        try:
            audit_entry = {
                "event_type": "bid_placed",
                "timestamp": datetime.now(timezone.utc),
                "player_id": player_id,
                "player_name": player_name,
                "team_id": team_id,
                "team_name": team_name,
                "bidder_id": bidder_id,
                "bidder_email": bidder_email,
                "bid_amount": bid_amount,
                "is_winning": is_winning,
                "metadata": {
                    "action": "bid",
                    "status": "winning" if is_winning else "outbid"
                }
            }
            
            db.audit_logs.insert_one(audit_entry)
            logger.debug(f"Audit: Bid logged - {player_name} by {team_name} for ₹{bid_amount}")
            
        except Exception as e:
            logger.error(f"Error logging bid audit: {e}")
    
    @staticmethod
    def log_player_sold(
        player_id: str,
        player_name: str,
        team_id: str,
        team_name: str,
        final_bid: float,
        admin_id: Optional[str] = None,
        admin_email: Optional[str] = None
    ):
        """
        Log a player sold event.
        
        Args:
            player_id: Player ID
            player_name: Player name
            team_id: Winning team ID
            team_name: Winning team name
            final_bid: Final bid amount
            admin_id: Admin who marked as sold (if manual)
            admin_email: Admin email
        """
        try:
            audit_entry = {
                "event_type": "player_sold",
                "timestamp": datetime.now(timezone.utc),
                "player_id": player_id,
                "player_name": player_name,
                "team_id": team_id,
                "team_name": team_name,
                "final_bid": final_bid,
                "admin_id": admin_id,
                "admin_email": admin_email,
                "metadata": {
                    "action": "sold",
                    "method": "manual" if admin_id else "auto"
                }
            }
            
            db.audit_logs.insert_one(audit_entry)
            logger.info(f"Audit: Player sold - {player_name} to {team_name} for ₹{final_bid}")
            
        except Exception as e:
            logger.error(f"Error logging player sold audit: {e}")
    
    @staticmethod
    def log_player_unsold(
        player_id: str,
        player_name: str,
        admin_id: Optional[str] = None,
        admin_email: Optional[str] = None
    ):
        """
        Log a player unsold event.
        
        Args:
            player_id: Player ID
            player_name: Player name
            admin_id: Admin who marked as unsold
            admin_email: Admin email
        """
        try:
            audit_entry = {
                "event_type": "player_unsold",
                "timestamp": datetime.now(timezone.utc),
                "player_id": player_id,
                "player_name": player_name,
                "admin_id": admin_id,
                "admin_email": admin_email,
                "metadata": {
                    "action": "unsold"
                }
            }
            
            db.audit_logs.insert_one(audit_entry)
            logger.info(f"Audit: Player unsold - {player_name}")
            
        except Exception as e:
            logger.error(f"Error logging player unsold audit: {e}")
    
    @staticmethod
    def log_admin_action(
        action: str,
        admin_id: str,
        admin_email: str,
        target_type: str,
        target_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log an admin action.
        
        Args:
            action: Action performed (e.g., "create_team", "delete_player")
            admin_id: Admin user ID
            admin_email: Admin email
            target_type: Type of target (team, player, user)
            target_id: Target ID
            details: Additional details
        """
        try:
            audit_entry = {
                "event_type": "admin_action",
                "timestamp": datetime.now(timezone.utc),
                "action": action,
                "admin_id": admin_id,
                "admin_email": admin_email,
                "target_type": target_type,
                "target_id": target_id,
                "details": details or {},
                "metadata": {
                    "category": "admin"
                }
            }
            
            db.audit_logs.insert_one(audit_entry)
            logger.info(f"Audit: Admin action - {action} by {admin_email} on {target_type} {target_id}")
            
        except Exception as e:
            logger.error(f"Error logging admin action audit: {e}")
    
    @staticmethod
    def log_team_purchase(
        team_id: str,
        team_name: str,
        player_id: str,
        player_name: str,
        purchase_price: float
    ):
        """
        Log a team purchase event.
        
        Args:
            team_id: Team ID
            team_name: Team name
            player_id: Player ID
            player_name: Player name
            purchase_price: Purchase price
        """
        try:
            audit_entry = {
                "event_type": "team_purchase",
                "timestamp": datetime.now(timezone.utc),
                "team_id": team_id,
                "team_name": team_name,
                "player_id": player_id,
                "player_name": player_name,
                "purchase_price": purchase_price,
                "metadata": {
                    "action": "purchase"
                }
            }
            
            db.audit_logs.insert_one(audit_entry)
            logger.info(f"Audit: Team purchase - {team_name} bought {player_name} for ₹{purchase_price}")
            
        except Exception as e:
            logger.error(f"Error logging team purchase audit: {e}")
    
    @staticmethod
    def log_auction_event(
        event: str,
        admin_id: Optional[str] = None,
        admin_email: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log an auction event (start, stop, reset).
        
        Args:
            event: Event type (start, stop, reset)
            admin_id: Admin user ID
            admin_email: Admin email
            details: Additional details
        """
        try:
            audit_entry = {
                "event_type": "auction_event",
                "timestamp": datetime.now(timezone.utc),
                "event": event,
                "admin_id": admin_id,
                "admin_email": admin_email,
                "details": details or {},
                "metadata": {
                    "category": "auction"
                }
            }
            
            db.audit_logs.insert_one(audit_entry)
            logger.info(f"Audit: Auction event - {event} by {admin_email}")
            
        except Exception as e:
            logger.error(f"Error logging auction event audit: {e}")
    
    @staticmethod
    def get_audit_logs(
        event_type: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> list:
        """
        Retrieve audit logs.
        
        Args:
            event_type: Filter by event type
            limit: Maximum number of logs to return
            skip: Number of logs to skip (pagination)
        
        Returns:
            List of audit log entries
        """
        try:
            query = {}
            if event_type:
                query["event_type"] = event_type
            
            logs = list(db.audit_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit))
            
            # Convert ObjectId to string
            for log in logs:
                log["_id"] = str(log["_id"])
                if log.get("timestamp"):
                    log["timestamp"] = log["timestamp"].isoformat()
            
            return logs
            
        except Exception as e:
            logger.error(f"Error retrieving audit logs: {e}")
            return []
    
    @staticmethod
    def get_audit_stats() -> Dict[str, Any]:
        """
        Get audit log statistics.
        
        Returns:
            Dictionary with audit statistics
        """
        try:
            # Count by event type
            pipeline = [
                {"$group": {
                    "_id": "$event_type",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ]
            
            event_counts = list(db.audit_logs.aggregate(pipeline))
            
            # Total logs
            total_logs = db.audit_logs.count_documents({})
            
            # Recent activity (last 24 hours)
            from datetime import timedelta
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            recent_logs = db.audit_logs.count_documents({
                "timestamp": {"$gte": yesterday}
            })
            
            return {
                "total_logs": total_logs,
                "recent_logs_24h": recent_logs,
                "by_event_type": {
                    item["_id"]: item["count"]
                    for item in event_counts
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting audit stats: {e}")
            return {
                "total_logs": 0,
                "recent_logs_24h": 0,
                "by_event_type": {}
            }


# Global audit logger instance
audit_logger = AuditLogger()
