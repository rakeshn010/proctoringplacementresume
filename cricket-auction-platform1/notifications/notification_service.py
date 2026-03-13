"""
Notification service for real-time alerts.
Uses WebSocket manager for broadcasting notifications.
"""
from typing import Dict, Any, Optional, Set
from datetime import datetime, timezone
import logging

from websocket.manager import manager
from database import db

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending real-time notifications."""
    
    async def notify_player_sold(
        self,
        player_id: str,
        player_name: str,
        final_bid: float,
        team_id: str,
        team_name: str
    ):
        """
        Notify all users when a player is sold.
        
        Args:
            player_id: Player ID
            player_name: Player name
            final_bid: Final bid amount
            team_id: Winning team ID
            team_name: Winning team name
        """
        try:
            notification = {
                "type": "notification_player_sold",
                "data": {
                    "player_id": player_id,
                    "player_name": player_name,
                    "final_bid": final_bid,
                    "team_id": team_id,
                    "team_name": team_name,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "priority": "high"
            }
            
            await manager.broadcast(notification)
            
            # Check wishlist and notify interested users
            await self._notify_wishlist_users(player_id, "sold", final_bid)
            
            logger.info(f"📢 Notified: Player {player_name} sold to {team_name} for ₹{final_bid}")
            
        except Exception as e:
            logger.error(f"Error sending player sold notification: {e}")
    
    async def notify_bid_update(
        self,
        player_id: str,
        player_name: str,
        bid_amount: float,
        team_id: str,
        team_name: str,
        bidder_id: str
    ):
        """
        Notify all users of a new bid.
        
        Args:
            player_id: Player ID
            player_name: Player name
            bid_amount: Bid amount
            team_id: Bidding team ID
            team_name: Bidding team name
            bidder_id: Bidder user ID
        """
        try:
            notification = {
                "type": "notification_bid_update",
                "data": {
                    "player_id": player_id,
                    "player_name": player_name,
                    "bid_amount": bid_amount,
                    "team_id": team_id,
                    "team_name": team_name,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "priority": "medium"
            }
            
            await manager.broadcast(notification)
            
            # Notify wishlist users
            await self._notify_wishlist_users(player_id, "bid", bid_amount)
            
        except Exception as e:
            logger.error(f"Error sending bid update notification: {e}")
    
    async def notify_auction_start(self):
        """Notify all users that auction has started."""
        try:
            notification = {
                "type": "notification_auction_start",
                "data": {
                    "message": "Auction has started!",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "priority": "high"
            }
            
            await manager.broadcast(notification)
            logger.info("📢 Notified: Auction started")
            
        except Exception as e:
            logger.error(f"Error sending auction start notification: {e}")
    
    async def notify_auction_stop(self):
        """Notify all users that auction has stopped."""
        try:
            notification = {
                "type": "notification_auction_stop",
                "data": {
                    "message": "Auction has stopped",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "priority": "high"
            }
            
            await manager.broadcast(notification)
            logger.info("📢 Notified: Auction stopped")
            
        except Exception as e:
            logger.error(f"Error sending auction stop notification: {e}")
    
    async def notify_player_live(
        self,
        player_id: str,
        player_name: str,
        base_price: float,
        role: Optional[str] = None
    ):
        """
        Notify all users when a player goes live.
        
        Args:
            player_id: Player ID
            player_name: Player name
            base_price: Base price
            role: Player role
        """
        try:
            notification = {
                "type": "notification_player_live",
                "data": {
                    "player_id": player_id,
                    "player_name": player_name,
                    "base_price": base_price,
                    "role": role,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "priority": "high"
            }
            
            await manager.broadcast(notification)
            
            # Notify wishlist users
            await self._notify_wishlist_users(player_id, "live", base_price)
            
            logger.info(f"📢 Notified: Player {player_name} is now live")
            
        except Exception as e:
            logger.error(f"Error sending player live notification: {e}")
    
    async def _notify_wishlist_users(
        self,
        player_id: str,
        event_type: str,
        price: float
    ):
        """
        Notify users who have this player in their wishlist.
        
        Args:
            player_id: Player ID
            event_type: Event type (sold, bid, live)
            price: Current/final price
        """
        try:
            # Find users with this player in wishlist
            wishlist_items = list(db.wishlist.find({"player_id": player_id}))
            
            if not wishlist_items:
                return
            
            # Get unique user IDs
            user_ids = set(item["user_id"] for item in wishlist_items)
            
            # Create notification
            notification = {
                "type": "notification_wishlist_alert",
                "data": {
                    "player_id": player_id,
                    "event_type": event_type,
                    "price": price,
                    "message": self._get_wishlist_message(event_type, price),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "priority": "medium"
            }
            
            # Send to specific users
            await manager.broadcast_to_users(notification, user_ids)
            
            logger.info(f"📢 Wishlist alert sent to {len(user_ids)} users for player {player_id}")
            
        except Exception as e:
            logger.error(f"Error sending wishlist notifications: {e}")
    
    def _get_wishlist_message(self, event_type: str, price: float) -> str:
        """Generate wishlist notification message."""
        if event_type == "sold":
            return f"A player from your wishlist was sold for ₹{price:,.0f}"
        elif event_type == "bid":
            return f"New bid on your wishlist player: ₹{price:,.0f}"
        elif event_type == "live":
            return f"A player from your wishlist is now live! Base price: ₹{price:,.0f}"
        else:
            return "Wishlist player update"
    
    async def notify_custom(
        self,
        message: str,
        notification_type: str = "info",
        user_ids: Optional[Set[str]] = None,
        priority: str = "low"
    ):
        """
        Send custom notification.
        
        Args:
            message: Notification message
            notification_type: Type of notification
            user_ids: Specific user IDs (None = broadcast to all)
            priority: Priority level (low, medium, high)
        """
        try:
            notification = {
                "type": f"notification_{notification_type}",
                "data": {
                    "message": message,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "priority": priority
            }
            
            if user_ids:
                await manager.broadcast_to_users(notification, user_ids)
            else:
                await manager.broadcast(notification)
            
            logger.info(f"📢 Custom notification sent: {message}")
            
        except Exception as e:
            logger.error(f"Error sending custom notification: {e}")


# Global notification service instance
notification_service = NotificationService()
