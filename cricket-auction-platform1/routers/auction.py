"""
Auction router.
Handles auction control, bidding, and real-time updates.
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Optional
from bson import ObjectId
import uuid

from core.security import get_current_user, require_admin
from services.auction_service import AuctionService
from services.bid_service import BidService
from schemas.auction import AuctionStatus, SetCurrentPlayerRequest
from schemas.bid import BidRequest
from websocket.manager import manager
from database import db
from datetime import datetime, timezone

router = APIRouter(prefix="/auction", tags=["Auction"])


@router.get("/status", response_model=AuctionStatus)
async def get_auction_status():
    """Get current auction status."""
    config = AuctionService.get_auction_config()
    current_player = AuctionService.get_current_player()
    
    return {
        "active": config.get("active", False),
        "current_player_id": config.get("current_player_id"),
        "current_player_name": current_player.get("name") if current_player else None,
        "timer_remaining": manager.timer_seconds if manager.timer_running else None
    }


@router.post("/start")
async def start_auction(current_user: Dict = Depends(require_admin)):
    """Start the auction (Admin only)."""
    return await AuctionService.start_auction()


@router.post("/stop")
async def stop_auction(current_user: Dict = Depends(require_admin)):
    """Stop the auction (Admin only)."""
    return await AuctionService.stop_auction()


@router.get("/current_player")
async def get_current_player():
    """Get the current auction player."""
    player = AuctionService.get_current_player()
    
    if not player:
        return {"message": "No current player"}
    
    return player


@router.post("/set_current_player/{player_id}")
async def set_current_player(
    player_id: str,
    current_user: Dict = Depends(require_admin)
):
    """Set the current auction player (Admin only)."""
    return await AuctionService.set_current_player(player_id)


@router.post("/next_player")
async def next_player(current_user: Dict = Depends(require_admin)):
    """Move to the next available player (Admin only)."""
    return await AuctionService.next_player()


@router.post("/start-reauction")
async def start_reauction(current_user: Dict = Depends(require_admin)):
    """
    Start re-auction for unsold players.
    Collects all unsold players and starts a new auction round.
    """
    # Get current auction round
    config = AuctionService.get_auction_config()
    current_round = config.get("auction_round", 1)
    next_round = current_round + 1
    
    # Find ALL unsold players (regardless of round)
    unsold_players = list(db.players.find({
        "status": "unsold"
    }))
    
    if not unsold_players:
        raise HTTPException(
            status_code=400,
            detail="No unsold players found for re-auction"
        )
    
    # Update ALL unsold players to new round and make them available
    db.players.update_many(
        {"status": "unsold"},
        {
            "$set": {
                "status": "available",
                "auction_round": next_round,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    # Update auction config
    config["auction_round"] = next_round
    config["active"] = True
    config["reauction_started_at"] = datetime.now(timezone.utc)
    
    db.config.update_one(
        {"key": "auction"},
        {"$set": {**config, "key": "auction"}},
        upsert=True
    )
    
    # Broadcast re-auction start
    await manager.broadcast_auction_status(True)
    
    return {
        "ok": True,
        "message": f"Re-auction round {next_round} started",
        "round": next_round,
        "unsold_players_count": len(unsold_players)
    }


@router.get("/unsold-players")
async def get_unsold_players(
    auction_round: Optional[int] = Query(None),
    current_user: Dict = Depends(require_admin)
):
    """Get all unsold players, optionally filtered by auction round."""
    query = {"status": "unsold"}
    
    if auction_round:
        query["auction_round"] = auction_round
    
    unsold = list(db.players.find(query))
    
    for player in unsold:
        player["_id"] = str(player["_id"])
    
    return {
        "ok": True,
        "unsold_players": unsold,
        "count": len(unsold)
    }


@router.get("/auction-rounds")
async def get_auction_rounds():
    """Get all auction rounds with statistics."""
    pipeline = [
        {
            "$group": {
                "_id": "$auction_round",
                "total_players": {"$sum": 1},
                "sold": {
                    "$sum": {"$cond": [{"$eq": ["$status", "sold"]}, 1, 0]}
                },
                "unsold": {
                    "$sum": {"$cond": [{"$eq": ["$status", "unsold"]}, 1, 0]}
                },
                "available": {
                    "$sum": {"$cond": [{"$eq": ["$status", "available"]}, 1, 0]}
                }
            }
        },
        {"$sort": {"_id": 1}}
    ]
    
    rounds = list(db.players.aggregate(pipeline))
    
    return {
        "ok": True,
        "rounds": [
            {
                "round": r["_id"],
                "total_players": r["total_players"],
                "sold": r["sold"],
                "unsold": r["unsold"],
                "available": r["available"]
            }
            for r in rounds
        ]
    }


@router.post("/sold/{player_id}")
async def mark_player_sold(
    player_id: str,
    current_user: Dict = Depends(require_admin)
):
    """Mark a player as sold (Admin only)."""
    return await AuctionService.mark_player_sold(player_id)


@router.post("/unsold/{player_id}")
async def mark_player_unsold(
    player_id: str,
    current_user: Dict = Depends(require_admin)
):
    """Mark a player as unsold (Admin only)."""
    return await AuctionService.mark_player_unsold(player_id)


@router.post("/bid")
async def place_bid(
    bid: BidRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Place a bid on the current player with rate limiting."""
    # Import rate limiter
    from core.rate_limiter import rate_limiter
    from core.config import settings
    
    # Apply rate limiting if enabled
    if settings.ENABLE_RATE_LIMITING:
        await rate_limiter.check_bid_rate_limit(current_user["user_id"])
    
    # Validate team membership for non-admin users
    if not current_user.get("is_admin"):
        if not current_user.get("team_id"):
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to any team"
            )
        
        if current_user["team_id"] != bid.team_id:
            raise HTTPException(
                status_code=403,
                detail="You can only bid for your own team"
            )
    
    return await BidService.place_bid(
        player_id=bid.player_id,
        team_id=bid.team_id,
        bid_amount=bid.bid_amount,
        bidder_id=current_user["user_id"]
    )


@router.get("/bid_history/{player_id}")
async def get_bid_history(player_id: str):
    """Get bid history for a specific player."""
    return BidService.get_bid_history(player_id)


@router.get("/bid_history")
async def get_all_bid_history(current_user: Dict = Depends(require_admin)):
    """Get complete bid history (Admin only). Updated 2026-02-14."""
    try:
        bids = list(db.bid_history.find().sort("timestamp", -1).limit(200))
        
        for bid in bids:
            bid["_id"] = str(bid["_id"])
            
            # Get player and team names with error handling
            try:
                player = db.players.find_one({"_id": ObjectId(bid["player_id"])})
                bid["player_name"] = player.get("name") if player else "Unknown"
            except Exception:
                bid["player_name"] = "Unknown"
            
            try:
                team = db.teams.find_one({"_id": ObjectId(bid["team_id"])})
                bid["team_name"] = team.get("name") if team else "Unknown"
            except Exception:
                bid["team_name"] = "Unknown"
        
        return {"ok": True, "bids": bids}
    except Exception as e:
        print(f"Error loading bid history: {e}")
        return {"ok": True, "bids": []}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time auction updates.
    Clients receive live bid updates, timer, and player changes.
    """
    connection_id = str(uuid.uuid4())
    
    await manager.connect(websocket, connection_id)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Optional: Handle client messages (e.g., heartbeat)
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(connection_id)
