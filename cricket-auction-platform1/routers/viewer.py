"""
Viewer router - Read-only endpoints for spectators.
Provides live auction data, analytics, and player browsing.
"""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
from bson import ObjectId

from database import db

router = APIRouter(prefix="/viewer", tags=["Viewer"])
templates = Jinja2Templates(directory="templates")


@router.get("/live", response_class=HTMLResponse)
async def live_viewer(request: Request):
    """Live auction viewer dashboard"""
    return templates.TemplateResponse("live_studio.html", {"request": request})


@router.get("/analytics")
async def get_viewer_analytics():
    """
    Get live auction analytics for viewer dashboard.
    Read-only endpoint with aggregated statistics.
    """
    try:
        # Get auction config
        config = db.config.find_one({"key": "auction"}) or {}
        
        # Count players by status
        total_players = db.players.count_documents({})
        sold_players = db.players.count_documents({"status": "sold"})
        unsold_players = db.players.count_documents({"status": "unsold"})
        available_players = db.players.count_documents({"status": "available"})
        
        # Calculate total revenue
        pipeline = [
            {"$match": {"status": "sold", "final_bid": {"$exists": True}}},
            {"$group": {"_id": None, "total": {"$sum": "$final_bid"}}}
        ]
        revenue_result = list(db.players.aggregate(pipeline))
        total_revenue = revenue_result[0]["total"] if revenue_result else 0
        
        # Find most expensive player
        most_expensive = db.players.find_one(
            {"status": "sold", "final_bid": {"$exists": True}},
            sort=[("final_bid", -1)]
        )
        
        # Get team spending leaderboard
        team_pipeline = [
            {"$match": {"status": "sold", "final_bid": {"$exists": True}, "final_team": {"$exists": True}}},
            {"$group": {
                "_id": "$final_team",
                "total_spent": {"$sum": "$final_bid"},
                "players_count": {"$sum": 1}
            }},
            {"$sort": {"total_spent": -1}}
        ]
        team_spending = list(db.players.aggregate(team_pipeline))
        
        # Get all teams with remaining purse
        teams = list(db.teams.find({}, {"name": 1, "budget": 1, "initial_budget": 1}))
        teams_data = []
        for team in teams:
            team_id = str(team["_id"])
            spent = next((t["total_spent"] for t in team_spending if str(t["_id"]) == team_id), 0)
            teams_data.append({
                "team_id": team_id,
                "name": team["name"],
                "remaining_purse": team.get("budget", 0),
                "total_spent": spent,
                "players_count": next((t["players_count"] for t in team_spending if str(t["_id"]) == team_id), 0)
            })
        
        # Sort teams by spending
        teams_data.sort(key=lambda x: x["total_spent"], reverse=True)
        
        return {
            "ok": True,
            "auction_active": config.get("active", False),
            "auction_round": config.get("auction_round", 1),
            "statistics": {
                "total_players": total_players,
                "sold_players": sold_players,
                "unsold_players": unsold_players,
                "available_players": available_players,
                "total_revenue": total_revenue,
                "most_expensive_player": {
                    "name": most_expensive["name"] if most_expensive else None,
                    "price": most_expensive.get("final_bid") if most_expensive else 0,
                    "team": most_expensive.get("final_team") if most_expensive else None
                } if most_expensive else None
            },
            "teams_leaderboard": teams_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current-player")
async def get_current_auction_player():
    """
    Get the player currently being auctioned.
    Returns player details with current highest bid.
    """
    try:
        config = db.config.find_one({"key": "auction"}) or {}
        
        if not config.get("active"):
            return {
                "ok": True,
                "auction_active": False,
                "current_player": None
            }
        
        current_player_id = config.get("current_player_id")
        
        if not current_player_id:
            return {
                "ok": True,
                "auction_active": True,
                "current_player": None
            }
        
        # Get player details
        player = db.players.find_one({"_id": ObjectId(current_player_id)})
        
        if not player:
            return {
                "ok": True,
                "auction_active": True,
                "current_player": None
            }
        
        # Get latest bid
        latest_bid = db.bid_history.find_one(
            {"player_id": current_player_id},
            sort=[("timestamp", -1)]
        )
        
        # Get team name if there's a bid
        leading_team = None
        if latest_bid and latest_bid.get("team_id"):
            team = db.teams.find_one({"_id": ObjectId(latest_bid["team_id"])})
            if team:
                leading_team = {
                    "id": str(team["_id"]),
                    "name": team["name"]
                }
        
        player_data = {
            "id": str(player["_id"]),
            "name": player["name"],
            "role": player.get("role"),
            "category": player.get("category"),
            "image_path": player.get("image_path") or player.get("photo") or player.get("image"),
            "base_price": player.get("base_price", 0),
            "current_bid": latest_bid.get("bid_amount") if latest_bid else player.get("base_price", 0),
            "leading_team": leading_team,
            "status": player.get("status", "available"),
            "age": player.get("age"),
            "batting_style": player.get("batting_style"),
            "bowling_style": player.get("bowling_style"),
            "bio": player.get("bio")
        }
        
        return {
            "ok": True,
            "auction_active": True,
            "current_player": player_data,
            "timer_seconds": config.get("timer_seconds", 30)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bid-history/{player_id}")
async def get_player_bid_history(player_id: str):
    """
    Get complete bid history for a specific player.
    Read-only endpoint for viewers.
    """
    try:
        bids = list(db.bid_history.find(
            {"player_id": player_id},
            sort=[("timestamp", -1)]
        ))
        
        bid_list = []
        for bid in bids:
            team = db.teams.find_one({"_id": ObjectId(bid["team_id"])})
            bid_list.append({
                "bid_amount": bid["bid_amount"],
                "team_name": team["name"] if team else "Unknown",
                "timestamp": bid["timestamp"].isoformat() if isinstance(bid["timestamp"], datetime) else str(bid["timestamp"])
            })
        
        return {
            "ok": True,
            "player_id": player_id,
            "bid_history": bid_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/players")
async def get_all_players_for_viewer():
    """
    Get all approved players for viewer dashboard.
    Read-only endpoint with basic player information.
    """
    try:
        players = list(db.players.find(
            {"is_approved": True},
            {
                "name": 1,
                "role": 1,
                "category": 1,
                "status": 1,
                "base_price": 1,
                "final_bid": 1,
                "final_team": 1,
                "image_path": 1,
                "photo": 1,
                "image": 1
            }
        ).sort("name", 1))
        
        # Serialize players
        player_list = []
        for player in players:
            player_data = {
                "id": str(player["_id"]),
                "name": player.get("name"),
                "role": player.get("role"),
                "category": player.get("category"),
                "status": player.get("status", "available"),
                "base_price": player.get("base_price", 0),
                "final_bid": player.get("final_bid"),
                "image_path": player.get("image_path") or player.get("photo") or player.get("image")
            }
            
            # Get team name if sold
            if player.get("final_team"):
                team = db.teams.find_one({"_id": ObjectId(player["final_team"])})
                if team:
                    player_data["team_name"] = team["name"]
            
            player_list.append(player_data)
        
        return {
            "ok": True,
            "players": player_list,
            "total": len(player_list)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
