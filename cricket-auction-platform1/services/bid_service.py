"""
Bid management service.
Handles bid placement, validation, and history tracking.
Enhanced with notification and audit logging (2026-03-13).
"""
from typing import Dict, Any, List
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException

from database import db
from core.config import settings
from websocket.manager import manager
from notifications.notification_service import notification_service
from audit_logging.audit_logger import audit_logger


class BidService:
    """Service for managing bid operations."""
    
    @staticmethod
    async def place_bid(
        player_id: str,
        team_id: str,
        bid_amount: float,
        bidder_id: str
    ) -> Dict[str, Any]:
        """
        Place a bid on a player.
        Validates bid amount, team budget, and auction status.
        """
        # Validate IDs
        try:
            pid = ObjectId(player_id)
            tid = ObjectId(team_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ID format")
        
        # Check auction is active
        config = db.config.find_one({"key": "auction"}) or {}
        if not config.get("active", False):
            raise HTTPException(status_code=400, detail="Auction is not active")
        
        # Check if timer is still running (prevent bids after timer expires)
        if not manager.timer_running or manager.timer_seconds <= 0:
            raise HTTPException(
                status_code=400, 
                detail="Auction time has expired. Please wait for admin to set next player."
            )
        
        # Get player
        player = db.players.find_one({"_id": pid})
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Prevent bidding on sold players
        if player.get("status") == "sold":
            raise HTTPException(status_code=400, detail="Cannot bid on sold player")
        
        # Prevent bidding on unsold players
        if player.get("status") == "unsold":
            raise HTTPException(status_code=400, detail="Cannot bid on unsold player")
        
        # Get team
        team = db.teams.find_one({"_id": tid})
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Validate bid amount
        if bid_amount <= 0:
            raise HTTPException(status_code=400, detail="Bid amount must be positive")
        
        current_highest = float(player.get("final_bid") or player.get("base_price") or 0)
        
        if bid_amount <= current_highest:
            raise HTTPException(
                status_code=400,
                detail=f"Bid must be higher than current highest bid (₹{current_highest})"
            )
        
        # Check minimum increment
        if current_highest > 0 and (bid_amount - current_highest) < settings.BID_INCREMENT:
            raise HTTPException(
                status_code=400,
                detail=f"Bid increment must be at least ₹{settings.BID_INCREMENT}"
            )
        
        # Check team budget
        team_budget = float(team.get("budget", 0))
        if bid_amount > team_budget:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient budget. Team has ₹{team_budget} remaining"
            )
        
        # Record bid in history
        bid_record = {
            "player_id": player_id,
            "team_id": team_id,
            "bidder_id": bidder_id,
            "bid_amount": bid_amount,
            "timestamp": datetime.now(timezone.utc),
            "is_winning": True
        }
        
        # Mark previous winning bid as not winning
        db.bid_history.update_many(
            {"player_id": player_id, "is_winning": True},
            {"$set": {"is_winning": False}}
        )
        
        # Insert new bid
        result = db.bid_history.insert_one(bid_record)
        
        # Update player with new highest bid
        db.players.update_one(
            {"_id": pid},
            {
                "$set": {
                    "final_bid": bid_amount,
                    "final_team": team_id,
                    "status": "in_auction",
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # Restore previous team's budget if they were outbid
        previous_team_id = player.get("final_team")
        if previous_team_id and previous_team_id != team_id:
            previous_bid = float(player.get("final_bid", 0))
            if previous_bid > 0:
                db.teams.update_one(
                    {"_id": ObjectId(previous_team_id)},
                    {"$inc": {"budget": previous_bid}}
                )
        
        # Deduct from new team's budget
        db.teams.update_one(
            {"_id": tid},
            {"$inc": {"budget": -bid_amount}}
        )
        
        # Reset auction timer
        manager.reset_timer(settings.AUCTION_TIMER_SECONDS)
        
        # Broadcast bid to all clients
        bid_data = {
            "player_id": player_id,
            "player_name": player.get("name"),
            "team_id": team_id,
            "team_name": team.get("name"),
            "bid_amount": bid_amount,
            "bidder_id": bidder_id
        }
        await manager.broadcast_bid(bid_data)
        
        # Broadcast team budget update
        updated_team = db.teams.find_one({"_id": tid})
        team_data = {
            "team_id": team_id,
            "team_name": updated_team.get("name"),
            "budget": updated_team.get("budget")
        }
        await manager.broadcast_team_update(team_data)
        
        # Send notification
        await notification_service.notify_bid_update(
            player_id=player_id,
            player_name=player.get("name"),
            bid_amount=bid_amount,
            team_id=team_id,
            team_name=team.get("name"),
            bidder_id=bidder_id
        )
        
        # Audit log
        # Get bidder email
        bidder = db.users.find_one({"_id": ObjectId(bidder_id)})
        bidder_email = bidder.get("email") if bidder else "unknown"
        
        audit_logger.log_bid(
            player_id=player_id,
            player_name=player.get("name"),
            team_id=team_id,
            team_name=team.get("name"),
            bidder_id=bidder_id,
            bidder_email=bidder_email,
            bid_amount=bid_amount,
            is_winning=True
        )
        
        return {
            "ok": True,
            "bid_id": str(result.inserted_id),
            **bid_data
        }
    
    @staticmethod
    def get_bid_history(player_id: str) -> List[Dict[str, Any]]:
        """Get bid history for a player."""
        try:
            pid = ObjectId(player_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid player ID")
        
        player = db.players.find_one({"_id": pid})
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        bids = list(db.bid_history.find(
            {"player_id": player_id}
        ).sort("timestamp", -1))
        
        # Enrich with team names
        for bid in bids:
            bid["_id"] = str(bid["_id"])
            team = db.teams.find_one({"_id": ObjectId(bid["team_id"])})
            if team:
                bid["team_name"] = team.get("name")
        
        return {
            "player_id": player_id,
            "player_name": player.get("name"),
            "bids": bids,
            "final_bid": player.get("final_bid"),
            "winning_team": player.get("final_team")
        }
    
    @staticmethod
    def get_all_bid_history() -> List[Dict[str, Any]]:
        """Get complete bid history for all players."""
        bids = list(db.bid_history.find().sort("timestamp", -1).limit(1000))
        
        for bid in bids:
            bid["_id"] = str(bid["_id"])
            
            # Enrich with player name
            player = db.players.find_one({"_id": ObjectId(bid["player_id"])})
            if player:
                bid["player_name"] = player.get("name")
            
            # Enrich with team name
            team = db.teams.find_one({"_id": ObjectId(bid["team_id"])})
            if team:
                bid["team_name"] = team.get("name")
        
        return bids
