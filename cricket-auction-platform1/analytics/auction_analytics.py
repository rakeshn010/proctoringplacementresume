"""
Advanced auction analytics engine.
Provides comprehensive analytics using MongoDB aggregation pipelines.
"""
from typing import Dict, List, Any
from datetime import datetime, timezone
import logging

from database import db

logger = logging.getLogger(__name__)


class AuctionAnalytics:
    """Advanced analytics for auction data."""
    
    @staticmethod
    def get_auction_summary() -> Dict[str, Any]:
        """
        Get comprehensive auction summary.
        
        Returns:
            Dictionary with auction statistics
        """
        try:
            # Total players
            total_players = db.players.count_documents({})
            sold_players = db.players.count_documents({"status": "sold"})
            unsold_players = db.players.count_documents({"status": "unsold"})
            
            # Revenue calculation
            revenue_pipeline = [
                {"$match": {"status": "sold", "final_bid": {"$exists": True}}},
                {"$group": {
                    "_id": None,
                    "total_revenue": {"$sum": "$final_bid"},
                    "avg_price": {"$avg": "$final_bid"},
                    "max_price": {"$max": "$final_bid"},
                    "min_price": {"$min": "$final_bid"}
                }}
            ]
            revenue_result = list(db.players.aggregate(revenue_pipeline))
            revenue_data = revenue_result[0] if revenue_result else {
                "total_revenue": 0,
                "avg_price": 0,
                "max_price": 0,
                "min_price": 0
            }
            
            # Most expensive player
            most_expensive = db.players.find_one(
                {"status": "sold", "final_bid": {"$exists": True}},
                sort=[("final_bid", -1)]
            )
            
            # Total bids
            total_bids = db.bid_history.count_documents({})
            
            return {
                "ok": True,
                "total_players": total_players,
                "sold_players": sold_players,
                "unsold_players": unsold_players,
                "available_players": total_players - sold_players - unsold_players,
                "total_revenue": revenue_data["total_revenue"],
                "average_price": revenue_data["avg_price"],
                "highest_price": revenue_data["max_price"],
                "lowest_price": revenue_data["min_price"],
                "total_bids": total_bids,
                "most_expensive_player": {
                    "name": most_expensive.get("name") if most_expensive else None,
                    "price": most_expensive.get("final_bid") if most_expensive else 0
                }
            }
        except Exception as e:
            logger.error(f"Error getting auction summary: {e}")
            return {"ok": False, "error": str(e)}
    
    @staticmethod
    def get_team_performance() -> Dict[str, Any]:
        """
        Analyze team performance and spending patterns.
        
        Returns:
            Dictionary with team performance metrics
        """
        try:
            # Team spending aggregation
            spending_pipeline = [
                {"$match": {"status": "sold", "final_bid": {"$exists": True}, "final_team": {"$exists": True}}},
                {"$group": {
                    "_id": "$final_team",
                    "total_spent": {"$sum": "$final_bid"},
                    "players_bought": {"$sum": 1},
                    "avg_price_paid": {"$avg": "$final_bid"},
                    "highest_purchase": {"$max": "$final_bid"}
                }},
                {"$sort": {"total_spent": -1}}
            ]
            
            spending_data = list(db.players.aggregate(spending_pipeline))
            
            # Enrich with team names
            teams_performance = []
            for team_data in spending_data:
                team_id = team_data["_id"]
                team = db.teams.find_one({"_id": team_id})
                
                if team:
                    initial_budget = team.get("budget", 0) + team_data["total_spent"]
                    
                    teams_performance.append({
                        "team_id": str(team_id),
                        "team_name": team.get("name"),
                        "total_spent": team_data["total_spent"],
                        "players_bought": team_data["players_bought"],
                        "avg_price_paid": team_data["avg_price_paid"],
                        "highest_purchase": team_data["highest_purchase"],
                        "remaining_budget": team.get("budget", 0),
                        "budget_used_percent": (team_data["total_spent"] / initial_budget * 100) if initial_budget > 0 else 0
                    })
            
            # Top spender
            top_spender = teams_performance[0] if teams_performance else None
            
            # Most efficient team (best value for money)
            if teams_performance:
                most_efficient = min(
                    teams_performance,
                    key=lambda t: t["avg_price_paid"] if t["players_bought"] > 0 else float('inf')
                )
            else:
                most_efficient = None
            
            return {
                "ok": True,
                "teams": teams_performance,
                "top_spender": top_spender,
                "most_efficient_team": most_efficient
            }
        except Exception as e:
            logger.error(f"Error getting team performance: {e}")
            return {"ok": False, "error": str(e)}
    
    @staticmethod
    def get_player_value_analysis() -> Dict[str, Any]:
        """
        Analyze player values by role and category.
        
        Returns:
            Dictionary with player value analysis
        """
        try:
            # Role-wise analysis
            role_pipeline = [
                {"$match": {"status": "sold", "final_bid": {"$exists": True}}},
                {"$group": {
                    "_id": "$role",
                    "count": {"$sum": 1},
                    "total_value": {"$sum": "$final_bid"},
                    "avg_price": {"$avg": "$final_bid"},
                    "max_price": {"$max": "$final_bid"},
                    "min_price": {"$min": "$final_bid"}
                }},
                {"$sort": {"avg_price": -1}}
            ]
            
            role_data = list(db.players.aggregate(role_pipeline))
            
            # Category-wise analysis
            category_pipeline = [
                {"$match": {"status": "sold", "final_bid": {"$exists": True}}},
                {"$group": {
                    "_id": "$category",
                    "count": {"$sum": 1},
                    "total_value": {"$sum": "$final_bid"},
                    "avg_price": {"$avg": "$final_bid"},
                    "max_price": {"$max": "$final_bid"},
                    "min_price": {"$min": "$final_bid"}
                }},
                {"$sort": {"avg_price": -1}}
            ]
            
            category_data = list(db.players.aggregate(category_pipeline))
            
            # Format results
            role_analysis = [{
                "role": r["_id"] or "Unknown",
                "players_sold": r["count"],
                "total_value": r["total_value"],
                "average_price": r["avg_price"],
                "highest_price": r["max_price"],
                "lowest_price": r["min_price"]
            } for r in role_data]
            
            category_analysis = [{
                "category": c["_id"] or "Unknown",
                "players_sold": c["count"],
                "total_value": c["total_value"],
                "average_price": c["avg_price"],
                "highest_price": c["max_price"],
                "lowest_price": c["min_price"]
            } for c in category_data]
            
            # Most valuable role
            most_valuable_role = role_analysis[0] if role_analysis else None
            
            return {
                "ok": True,
                "by_role": role_analysis,
                "by_category": category_analysis,
                "most_valuable_role": most_valuable_role
            }
        except Exception as e:
            logger.error(f"Error getting player value analysis: {e}")
            return {"ok": False, "error": str(e)}
    
    @staticmethod
    def get_auction_trends() -> Dict[str, Any]:
        """
        Get auction revenue trends over time.
        
        Returns:
            Dictionary with trend data
        """
        try:
            # Bidding activity over time
            bid_timeline_pipeline = [
                {"$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:00",
                            "date": "$timestamp"
                        }
                    },
                    "bid_count": {"$sum": 1},
                    "total_value": {"$sum": "$bid_amount"}
                }},
                {"$sort": {"_id": 1}},
                {"$limit": 24}  # Last 24 hours
            ]
            
            bid_timeline = list(db.bid_history.aggregate(bid_timeline_pipeline))
            
            # Round-wise statistics
            round_pipeline = [
                {"$match": {"status": "sold"}},
                {"$group": {
                    "_id": "$auction_round",
                    "players_sold": {"$sum": 1},
                    "total_revenue": {"$sum": "$final_bid"},
                    "avg_price": {"$avg": "$final_bid"}
                }},
                {"$sort": {"_id": 1}}
            ]
            
            round_stats = list(db.players.aggregate(round_pipeline))
            
            return {
                "ok": True,
                "bid_timeline": [{
                    "hour": item["_id"],
                    "bids": item["bid_count"],
                    "value": item["total_value"]
                } for item in bid_timeline],
                "round_statistics": [{
                    "round": r["_id"],
                    "players_sold": r["players_sold"],
                    "total_revenue": r["total_revenue"],
                    "average_price": r["avg_price"]
                } for r in round_stats]
            }
        except Exception as e:
            logger.error(f"Error getting auction trends: {e}")
            return {"ok": False, "error": str(e)}


# Global analytics instance
auction_analytics = AuctionAnalytics()
