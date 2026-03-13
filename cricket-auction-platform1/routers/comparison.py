"""
Team comparison router.
Handles team-to-team comparisons and squad analysis.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from bson import ObjectId

from database import db
from core.security import get_current_user

router = APIRouter(prefix="/comparison", tags=["Comparison"])


@router.get("/teams")
async def compare_teams(
    team_ids: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Compare multiple teams.
    team_ids: comma-separated team IDs (e.g., "id1,id2,id3")
    """
    try:
        # Parse team IDs
        team_id_list = [tid.strip() for tid in team_ids.split(",")]
        
        if len(team_id_list) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 teams to compare")
        
        if len(team_id_list) > 4:
            raise HTTPException(status_code=400, detail="Maximum 4 teams can be compared")
        
        comparison_data = []
        
        for team_id in team_id_list:
            try:
                tid = ObjectId(team_id)
            except:
                continue
            
            # Get team data
            team = db.teams.find_one({"_id": tid})
            if not team:
                continue
            
            # Get team's players
            players = list(db.players.find({
                "final_team": team_id,
                "status": "sold"
            }))
            
            # Calculate statistics
            total_spent = sum(p.get("final_bid", 0) for p in players)
            avg_price = total_spent / len(players) if players else 0
            
            # Role distribution
            role_dist = {}
            for player in players:
                role = player.get("role", "Unknown")
                role_dist[role] = role_dist.get(role, 0) + 1
            
            # Category distribution
            category_dist = {}
            for player in players:
                cat = player.get("category", "Unknown")
                category_dist[cat] = category_dist.get(cat, 0) + 1
            
            # Most expensive player
            most_expensive = max(players, key=lambda p: p.get("final_bid", 0)) if players else None
            
            # Cheapest player
            cheapest = min(players, key=lambda p: p.get("final_bid", 0)) if players else None
            
            comparison_data.append({
                "team_id": team_id,
                "team_name": team.get("name"),
                "total_budget": team.get("budget", 0),
                "total_spent": total_spent,
                "remaining_budget": team.get("budget", 0) - total_spent,
                "budget_used_percent": (total_spent / team.get("budget", 1)) * 100,
                "players_count": len(players),
                "average_price": avg_price,
                "role_distribution": role_dist,
                "category_distribution": category_dist,
                "most_expensive_player": {
                    "name": most_expensive.get("name"),
                    "price": most_expensive.get("final_bid"),
                    "role": most_expensive.get("role")
                } if most_expensive else None,
                "cheapest_player": {
                    "name": cheapest.get("name"),
                    "price": cheapest.get("final_bid"),
                    "role": cheapest.get("role")
                } if cheapest else None,
                "squad_balance_score": calculate_squad_balance(role_dist),
                "value_for_money_score": calculate_value_score(players, total_spent)
            })
        
        return {
            "ok": True,
            "teams": comparison_data,
            "comparison_count": len(comparison_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing teams: {str(e)}")


def calculate_squad_balance(role_dist: dict) -> float:
    """
    Calculate squad balance score (0-100).
    Ideal distribution: 4 batsmen, 4 bowlers, 2 all-rounders, 1 wicketkeeper
    """
    ideal = {
        "Batsman": 4,
        "Bowler": 4,
        "All-Rounder": 2,
        "Wicketkeeper": 1
    }
    
    total_deviation = 0
    for role, ideal_count in ideal.items():
        actual_count = role_dist.get(role, 0)
        deviation = abs(actual_count - ideal_count)
        total_deviation += deviation
    
    # Convert to score (lower deviation = higher score)
    max_deviation = 11  # Maximum possible deviation
    score = max(0, 100 - (total_deviation / max_deviation * 100))
    
    return round(score, 1)


def calculate_value_score(players: list, total_spent: int) -> float:
    """
    Calculate value for money score (0-100).
    Based on player quality vs price paid.
    """
    if not players or total_spent == 0:
        return 0.0
    
    # Simple heuristic: more players for less money = better value
    avg_price = total_spent / len(players)
    
    # Ideal average price (adjust based on your auction)
    ideal_avg = 5000
    
    if avg_price <= ideal_avg:
        score = 100
    else:
        # Penalty for spending more than ideal
        score = max(0, 100 - ((avg_price - ideal_avg) / ideal_avg * 50))
    
    return round(score, 1)


@router.get("/my-team-analysis")
async def analyze_my_team(current_user: dict = Depends(get_current_user)):
    """Get detailed analysis of current user's team."""
    try:
        team_id = current_user.get("team_id")
        if not team_id:
            raise HTTPException(status_code=400, detail="User not associated with a team")
        
        team = db.teams.find_one({"_id": ObjectId(team_id)})
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Get team's players
        players = list(db.players.find({
            "final_team": team_id,
            "status": "sold"
        }))
        
        # Detailed analysis
        analysis = {
            "team_name": team.get("name"),
            "total_players": len(players),
            "total_spent": sum(p.get("final_bid", 0) for p in players),
            "remaining_budget": team.get("budget", 0) - sum(p.get("final_bid", 0) for p in players),
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        }
        
        # Role analysis
        role_counts = {}
        for player in players:
            role = player.get("role", "Unknown")
            role_counts[role] = role_counts.get(role, 0) + 1
        
        # Identify strengths and weaknesses
        if role_counts.get("Batsman", 0) >= 4:
            analysis["strengths"].append("Strong batting lineup")
        elif role_counts.get("Batsman", 0) < 2:
            analysis["weaknesses"].append("Weak batting lineup")
            analysis["recommendations"].append("Consider buying more batsmen")
        
        if role_counts.get("Bowler", 0) >= 4:
            analysis["strengths"].append("Strong bowling attack")
        elif role_counts.get("Bowler", 0) < 2:
            analysis["weaknesses"].append("Weak bowling attack")
            analysis["recommendations"].append("Consider buying more bowlers")
        
        if role_counts.get("All-Rounder", 0) >= 2:
            analysis["strengths"].append("Good all-round balance")
        elif role_counts.get("All-Rounder", 0) == 0:
            analysis["weaknesses"].append("No all-rounders")
            analysis["recommendations"].append("All-rounders provide flexibility")
        
        if role_counts.get("Wicketkeeper", 0) >= 1:
            analysis["strengths"].append("Wicketkeeper secured")
        else:
            analysis["weaknesses"].append("No wicketkeeper")
            analysis["recommendations"].append("Must have at least one wicketkeeper")
        
        # Budget analysis
        budget_remaining_percent = (analysis["remaining_budget"] / team.get("budget", 1)) * 100
        if budget_remaining_percent > 50:
            analysis["recommendations"].append(f"You have {budget_remaining_percent:.1f}% budget remaining - consider aggressive bidding")
        elif budget_remaining_percent < 10:
            analysis["recommendations"].append("Budget is low - bid carefully")
        
        return {"ok": True, "analysis": analysis}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing team: {str(e)}")
