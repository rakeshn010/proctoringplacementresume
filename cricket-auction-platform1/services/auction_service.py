"""
Auction business logic service.
Handles auction state management, player transitions, and timer logic.
Enhanced with notification service integration (2026-03-13).
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException

from database import db
from core.config import settings
from websocket.manager import manager
from notifications.notification_service import notification_service
from audit_logging.audit_logger import audit_logger


class AuctionService:
    """Service for managing auction operations."""
    
    @staticmethod
    def get_auction_config() -> Dict[str, Any]:
        """Get current auction configuration."""
        config = db.config.find_one({"key": "auction"}) or {}
        if "active" not in config:
            config["active"] = False
        return config
    
    @staticmethod
    async def start_auction() -> Dict[str, Any]:
        """Start the auction."""
        config = AuctionService.get_auction_config()
        config["active"] = True
        config["started_at"] = datetime.now(timezone.utc)
        
        db.config.update_one(
            {"key": "auction"},
            {"$set": {**config, "key": "auction"}},
            upsert=True
        )
        
        # Broadcast to all connected clients
        await manager.broadcast_auction_status(True)
        
        # Send notification
        await notification_service.notify_auction_start()
        
        # Audit log
        audit_logger.log_auction_event("start")
        
        return {"ok": True, "message": "Auction started"}
    
    @staticmethod
    async def stop_auction() -> Dict[str, Any]:
        """Stop the auction."""
        config = AuctionService.get_auction_config()
        config["active"] = False
        config["stopped_at"] = datetime.now(timezone.utc)
        
        db.config.update_one(
            {"key": "auction"},
            {"$set": {**config, "key": "auction"}},
            upsert=True
        )
        
        # Stop timer and broadcast
        manager.stop_timer()
        await manager.broadcast_auction_status(False)
        
        return {"ok": True, "message": "Auction stopped"}
    
    @staticmethod
    def get_current_player() -> Optional[Dict[str, Any]]:
        """Get the current auction player."""
        config = AuctionService.get_auction_config()
        player_id = config.get("current_player_id")
        
        if not player_id:
            return None
        
        try:
            player = db.players.find_one({"_id": ObjectId(player_id)})
            if player:
                player["_id"] = str(player["_id"])
            return player
        except Exception:
            return None
    
    @staticmethod
    async def set_current_player(player_id: str) -> Dict[str, Any]:
        """Set the current auction player."""
        try:
            pid = ObjectId(player_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid player ID")
        
        player = db.players.find_one({"_id": pid})
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Update config
        db.config.update_one(
            {"key": "auction"},
            {"$set": {"current_player_id": player_id}},
            upsert=True
        )
        
        # Reset timer
        manager.reset_timer(settings.AUCTION_TIMER_SECONDS)
        
        # Broadcast to all clients
        player["_id"] = str(player["_id"])
        await manager.broadcast_current_player(player)
        
        return {"ok": True, "player": player}
    
    @staticmethod
    async def next_player() -> Dict[str, Any]:
        """Move to the next available player."""
        next_player = db.players.find_one(
            {"status": "available"},
            sort=[("_id", 1)]
        )
        
        if not next_player:
            return {"ok": False, "message": "No more available players"}
        
        player_id = str(next_player["_id"])
        return await AuctionService.set_current_player(player_id)
    
    @staticmethod
    async def mark_player_sold(player_id: str) -> Dict[str, Any]:
        """Mark a player as sold."""
        try:
            pid = ObjectId(player_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid player ID")
        
        player = db.players.find_one({"_id": pid})
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Check if already sold
        if player.get("status") == "sold":
            raise HTTPException(status_code=400, detail="Player already sold")
        
        final_bid = player.get("final_bid")
        final_team = player.get("final_team")
        
        if final_bid is None or final_team is None:
            raise HTTPException(
                status_code=400,
                detail="Player must have a bid before marking as sold"
            )
        
        # Update player status
        db.players.update_one(
            {"_id": pid},
            {
                "$set": {
                    "status": "sold",
                    "final_bid": float(final_bid),
                    "final_team": str(final_team),
                    "sold_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # Broadcast sold event
        player["_id"] = str(player["_id"])
        player["status"] = "sold"
        await manager.broadcast_player_sold(player)
        
        return {
            "ok": True,
            "player_id": player_id,
            "final_bid": final_bid,
            "final_team": final_team,
            "status": "sold"
        }
    
    @staticmethod
    async def mark_player_unsold(player_id: str) -> Dict[str, Any]:
        """Mark a player as unsold."""
        try:
            pid = ObjectId(player_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid player ID")
        
        player = db.players.find_one({"_id": pid})
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Restore team budget if there was a bid
        if player.get("final_bid") and player.get("final_team"):
            try:
                team_id = ObjectId(player["final_team"])
                db.teams.update_one(
                    {"_id": team_id},
                    {"$inc": {"budget": float(player["final_bid"])}}
                )
            except Exception:
                pass
        
        # Update player status
        db.players.update_one(
            {"_id": pid},
            {
                "$set": {
                    "status": "unsold",
                    "updated_at": datetime.now(timezone.utc)
                },
                "$unset": {
                    "final_bid": "",
                    "final_team": "",
                    "current_team": ""
                }
            }
        )
        
        # Broadcast unsold event
        player["_id"] = str(player["_id"])
        player["status"] = "unsold"
        await manager.broadcast_player_unsold(player)
        
        return {"ok": True, "player_id": player_id, "status": "unsold"}
