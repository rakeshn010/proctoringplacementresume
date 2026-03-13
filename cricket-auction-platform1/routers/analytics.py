"""
Analytics router for auction data analysis.
Provides comprehensive analytics endpoints.
"""
from fastapi import APIRouter, Depends
from analytics.auction_analytics import auction_analytics
from core.security import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/auction-summary")
async def get_auction_summary(current_user: dict = Depends(get_current_user)):
    """
    Get comprehensive auction summary.
    
    Includes:
    - Total players (sold/unsold/available)
    - Revenue statistics
    - Most expensive player
    - Total bids
    """
    return auction_analytics.get_auction_summary()


@router.get("/team-performance")
async def get_team_performance(current_user: dict = Depends(get_current_user)):
    """
    Analyze team performance and spending patterns.
    
    Includes:
    - Total spending per team
    - Players bought
    - Average price paid
    - Budget utilization
    - Top spender
    - Most efficient team
    """
    return auction_analytics.get_team_performance()


@router.get("/player-value-analysis")
async def get_player_value_analysis(current_user: dict = Depends(get_current_user)):
    """
    Analyze player values by role and category.
    
    Includes:
    - Role-wise statistics (Batsman, Bowler, etc.)
    - Category-wise statistics (Faculty, Student, Alumni)
    - Average prices
    - Most valuable role
    """
    return auction_analytics.get_player_value_analysis()


@router.get("/auction-trends")
async def get_auction_trends(current_user: dict = Depends(get_current_user)):
    """
    Get auction revenue trends over time.
    
    Includes:
    - Bidding activity timeline
    - Round-wise statistics
    - Revenue trends
    """
    return auction_analytics.get_auction_trends()
