"""
Player wishlist router.
Handles player favorites, wishlist management, and notifications.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from bson import ObjectId
from datetime import datetime, timezone

from database import db
from core.security import get_current_user

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.post("/add/{player_id}")
async def add_to_wishlist(
    player_id: str,
    priority: int = 3,
    max_bid: int = None,
    current_user: dict = Depends(get_current_user)
):
    """Add a player to wishlist."""
    try:
        pid = ObjectId(player_id)
        
        # Check if player exists
        player = db.players.find_one({"_id": pid})
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Check if already in wishlist
        existing = db.wishlist.find_one({
            "user_id": current_user.get("user_id"),
            "player_id": str(pid)
        })
        
        if existing:
            raise HTTPException(status_code=400, detail="Player already in wishlist")
        
        # Add to wishlist
        wishlist_item = {
            "user_id": current_user.get("user_id"),
            "team_id": current_user.get("team_id"),
            "player_id": str(pid),
            "player_name": player.get("name"),
            "priority": priority,  # 1=High, 2=Medium, 3=Low
            "max_bid": max_bid,
            "added_at": datetime.now(timezone.utc),
            "notified": False
        }
        
        result = db.wishlist.insert_one(wishlist_item)
        
        return {
            "ok": True,
            "wishlist_id": str(result.inserted_id),
            "message": f"{player.get('name')} added to wishlist"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding to wishlist: {str(e)}")


@router.delete("/remove/{player_id}")
async def remove_from_wishlist(
    player_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a player from wishlist."""
    try:
        result = db.wishlist.delete_one({
            "user_id": current_user.get("user_id"),
            "player_id": player_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Player not in wishlist")
        
        return {"ok": True, "message": "Player removed from wishlist"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing from wishlist: {str(e)}")


@router.get("/my-wishlist")
async def get_my_wishlist(current_user: dict = Depends(get_current_user)):
    """Get current user's wishlist."""
    try:
        wishlist_items = list(db.wishlist.find({
            "user_id": current_user.get("user_id")
        }).sort("priority", 1))
        
        # Get full player details
        for item in wishlist_items:
            item["_id"] = str(item["_id"])
            player = db.players.find_one({"_id": ObjectId(item["player_id"])})
            if player:
                item["player_details"] = {
                    "name": player.get("name"),
                    "role": player.get("role"),
                    "category": player.get("category"),
                    "base_price": player.get("base_price"),
                    "status": player.get("status"),
                    "image_path": player.get("image_path"),
                    "is_live": player.get("is_live", False)
                }
        
        return {
            "ok": True,
            "wishlist": wishlist_items,
            "count": len(wishlist_items)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting wishlist: {str(e)}")


@router.patch("/update/{player_id}")
async def update_wishlist_item(
    player_id: str,
    priority: int = None,
    max_bid: int = None,
    current_user: dict = Depends(get_current_user)
):
    """Update wishlist item priority or max bid."""
    try:
        update_fields = {}
        if priority is not None:
            update_fields["priority"] = priority
        if max_bid is not None:
            update_fields["max_bid"] = max_bid
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        result = db.wishlist.update_one(
            {
                "user_id": current_user.get("user_id"),
                "player_id": player_id
            },
            {"$set": update_fields}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Player not in wishlist")
        
        return {"ok": True, "message": "Wishlist updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating wishlist: {str(e)}")


@router.get("/check/{player_id}")
async def check_wishlist(
    player_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if a player is in wishlist."""
    try:
        item = db.wishlist.find_one({
            "user_id": current_user.get("user_id"),
            "player_id": player_id
        })
        
        return {
            "ok": True,
            "in_wishlist": item is not None,
            "priority": item.get("priority") if item else None,
            "max_bid": item.get("max_bid") if item else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking wishlist: {str(e)}")
