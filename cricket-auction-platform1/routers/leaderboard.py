"""
Leaderboard router for rankings and top performers.
Provides various leaderboards for teams and players.
"""
from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from bson import ObjectId

from database import db
from core.security import get_current_user

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get("/top-spenders")
async def get_top_spenders(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Get top spending teams leaderboard.
    
    Ranks teams by total spending.
    """
    try:
        # Aggregate spending by team
        pipeline = [
            {"$match": {"status": "sold", "final_bid": {"$exists": True}, "final_team": {"$exists": True}}},
            {"$group": {
                "_id": "$final_team",
                "total_spent": {"$sum": "$final_bid"},
                "players_bought": {"$sum": 1},
                "highest_purchase": {"$max": "$final_bid"}
            }},
            {"$sort": {"total_spent": -1}},
            {"$limit": limit}
        ]
        
        spending_data = list(db.players.aggregate(pipeline))
        
        # Enrich with team details
        leaderboard = []
        rank = 1
        
        for entry in spending_data:
            team = db.teams.find_one({"_id": ObjectId(entry["_id"])})
            if team:
                leaderboard.append({
                    "rank": rank,
                    "team_id": str(entry["_id"]),
                    "team_name": team.get("name"),
                    "total_spent": entry["total_spent"],
                    "players_bought": entry["players_bought"],
                    "highest_purchase": entry["highest_purchase"],
                    "remaining_budget": team.get("budget", 0)
                })
                rank += 1
        
        return {
            "ok": True,
            "leaderboard": leaderboard,
            "total_entries": len(leaderboard)
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/top-teams")
async def get_top_teams(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Get top teams by value for money index.
    
    Ranks teams by efficiency (players bought vs money spent).
    """
    try:
        # Aggregate team data
        pipeline = [
            {"$match": {"status": "sold", "final_bid": {"$exists": True}, "final_team": {"$exists": True}}},
            {"$group": {
                "_id": "$final_team",
                "total_spent": {"$sum": "$final_bid"},
                "players_bought": {"$sum": 1},
                "avg_price": {"$avg": "$final_bid"}
            }}
        ]
        
        team_data = list(db.players.aggregate(pipeline))
        
        # Calculate value for money index
        teams_with_index = []
        
        for entry in team_data:
            team = db.teams.find_one({"_id": ObjectId(entry["_id"])})
            if team:
                # Value for money: more players for less money = better
                # Index = (players_bought * 10000) / avg_price
                value_index = (entry["players_bought"] * 10000) / entry["avg_price"] if entry["avg_price"] > 0 else 0
                
                teams_with_index.append({
                    "team_id": str(entry["_id"]),
                    "team_name": team.get("name"),
                    "total_spent": entry["total_spent"],
                    "players_bought": entry["players_bought"],
                    "avg_price": entry["avg_price"],
                    "value_for_money_index": round(value_index, 2),
                    "remaining_budget": team.get("budget", 0)
                })
        
        # Sort by value index
        teams_with_index.sort(key=lambda x: x["value_for_money_index"], reverse=True)
        
        # Add ranks
        leaderboard = []
        for rank, team in enumerate(teams_with_index[:limit], 1):
            team["rank"] = rank
            leaderboard.append(team)
        
        return {
            "ok": True,
            "leaderboard": leaderboard,
            "total_entries": len(leaderboard),
            "description": "Teams ranked by value for money (higher is better)"
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/top-players")
async def get_top_players(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Get top players by auction price.
    
    Ranks players by final bid amount.
    """
    try:
        # Get top sold players
        players = list(db.players.find(
            {"status": "sold", "final_bid": {"$exists": True}},
            {
                "name": 1,
                "role": 1,
                "category": 1,
                "final_bid": 1,
                "final_team": 1,
                "image_path": 1
            }
        ).sort("final_bid", -1).limit(limit))
        
        # Enrich with team names
        leaderboard = []
        rank = 1
        
        for player in players:
            team_name = None
            if player.get("final_team"):
                team = db.teams.find_one({"_id": ObjectId(player["final_team"])})
                if team:
                    team_name = team.get("name")
            
            leaderboard.append({
                "rank": rank,
                "player_id": str(player["_id"]),
                "player_name": player.get("name"),
                "role": player.get("role"),
                "category": player.get("category"),
                "final_bid": player.get("final_bid"),
                "team_name": team_name,
                "image_path": player.get("image_path")
            })
            rank += 1
        
        return {
            "ok": True,
            "leaderboard": leaderboard,
            "total_entries": len(leaderboard)
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/most-active-bidders")
async def get_most_active_bidders(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Get most active bidders leaderboard.
    
    Ranks teams by number of bids placed.
    """
    try:
        # Aggregate bid counts by team
        pipeline = [
            {"$group": {
                "_id": "$team_id",
                "total_bids": {"$sum": 1},
                "total_bid_value": {"$sum": "$bid_amount"},
                "winning_bids": {
                    "$sum": {"$cond": [{"$eq": ["$is_winning", True]}, 1, 0]}
                }
            }},
            {"$sort": {"total_bids": -1}},
            {"$limit": limit}
        ]
        
        bid_data = list(db.bid_history.aggregate(pipeline))
        
        # Enrich with team details
        leaderboard = []
        rank = 1
        
        for entry in bid_data:
            team = db.teams.find_one({"_id": ObjectId(entry["_id"])})
            if team:
                success_rate = (entry["winning_bids"] / entry["total_bids"] * 100) if entry["total_bids"] > 0 else 0
                
                leaderboard.append({
                    "rank": rank,
                    "team_id": str(entry["_id"]),
                    "team_name": team.get("name"),
                    "total_bids": entry["total_bids"],
                    "winning_bids": entry["winning_bids"],
                    "success_rate": round(success_rate, 2),
                    "total_bid_value": entry["total_bid_value"]
                })
                rank += 1
        
        return {
            "ok": True,
            "leaderboard": leaderboard,
            "total_entries": len(leaderboard),
            "description": "Teams ranked by bidding activity"
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/combined-leaderboard")
async def get_combined_leaderboard(current_user: dict = Depends(get_current_user)):
    """
    Get combined leaderboard with multiple metrics.
    
    Provides a comprehensive view of all teams.
    """
    try:
        # Get all teams
        teams = list(db.teams.find())
        
        combined = []
        
        for team in teams:
            team_id = str(team["_id"])
            
            # Get spending data
            players = list(db.players.find({"final_team": team_id, "status": "sold"}))
            total_spent = sum(p.get("final_bid", 0) for p in players)
            players_count = len(players)
            highest_purchase = max([p.get("final_bid", 0) for p in players], default=0)
            
            # Get bidding data
            bid_count = db.bid_history.count_documents({"team_id": team_id})
            winning_bids = db.bid_history.count_documents({"team_id": team_id, "is_winning": True})
            
            # Calculate scores
            avg_price = total_spent / players_count if players_count > 0 else 0
            value_index = (players_count * 10000) / avg_price if avg_price > 0 else 0
            success_rate = (winning_bids / bid_count * 100) if bid_count > 0 else 0
            
            combined.append({
                "team_id": team_id,
                "team_name": team.get("name"),
                "total_spent": total_spent,
                "players_bought": players_count,
                "highest_purchase": highest_purchase,
                "remaining_budget": team.get("budget", 0),
                "total_bids": bid_count,
                "winning_bids": winning_bids,
                "success_rate": round(success_rate, 2),
                "value_for_money_index": round(value_index, 2)
            })
        
        # Sort by total spent (default)
        combined.sort(key=lambda x: x["total_spent"], reverse=True)
        
        # Add ranks
        for rank, team in enumerate(combined, 1):
            team["rank"] = rank
        
        return {
            "ok": True,
            "leaderboard": combined,
            "total_entries": len(combined)
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}
