"""
Reports router.
Handles export functionality for auction data.
"""
from fastapi import APIRouter, HTTPException, Depends, Response
from typing import Optional
import io
from datetime import datetime

from database import db
from core.security import require_admin

router = APIRouter(prefix="/reports", tags=["Reports"])


try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


@router.get("/export/sold-players")
async def export_sold_players(
    format: str = "csv",
    current_user: dict = Depends(require_admin)
):
    """Export sold players to CSV or Excel."""
    if not PANDAS_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="Export functionality requires pandas and openpyxl"
        )
    
    # Get sold players
    players = list(db.players.find({"status": "sold"}))
    
    if not players:
        raise HTTPException(status_code=404, detail="No sold players found")
    
    # Prepare data
    data = []
    for p in players:
        team = db.teams.find_one({"_id": p.get("final_team")}) if p.get("final_team") else None
        
        data.append({
            "Player Name": p.get("name"),
            "Category": p.get("category"),
            "Base Price": p.get("base_price"),
            "Final Bid": p.get("final_bid"),
            "Team": team.get("name") if team else "N/A",
            "Affiliation": p.get("affiliation_role"),
            "Age": p.get("age"),
            "Batting Style": p.get("batting_style"),
            "Bowling Style": p.get("bowling_style")
        })
    
    df = pd.DataFrame(data)
    
    # Generate file
    if format == "excel":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sold Players')
        output.seek(0)
        
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=sold_players_{datetime.now().strftime('%Y%m%d')}.xlsx"
            }
        )
    else:
        csv_data = df.to_csv(index=False)
        
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=sold_players_{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )


@router.get("/export/team-summary")
async def export_team_summary(
    format: str = "csv",
    current_user: dict = Depends(require_admin)
):
    """Export team-wise summary."""
    if not PANDAS_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="Export functionality requires pandas and openpyxl"
        )
    
    teams = list(db.teams.find({}))
    
    data = []
    for team in teams:
        team_id = str(team["_id"])
        players = list(db.players.find({"final_team": team_id, "status": "sold"}))
        
        total_spent = sum(p.get("final_bid", 0) for p in players)
        
        data.append({
            "Team Name": team.get("name"),
            "Owner": team.get("owner"),
            "Initial Budget": team.get("budget", 0) + total_spent,
            "Total Spent": total_spent,
            "Remaining Budget": team.get("budget", 0),
            "Players Count": len(players)
        })
    
    df = pd.DataFrame(data)
    
    if format == "excel":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Team Summary')
        output.seek(0)
        
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=team_summary_{datetime.now().strftime('%Y%m%d')}.xlsx"
            }
        )
    else:
        csv_data = df.to_csv(index=False)
        
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=team_summary_{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )


@router.get("/export/auction-summary")
async def export_auction_summary(
    format: str = "csv",
    current_user: dict = Depends(require_admin)
):
    """Export complete auction summary."""
    if not PANDAS_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="Export functionality requires pandas and openpyxl"
        )
    
    # Get all players
    players = list(db.players.find({}))
    
    data = []
    for p in players:
        team = None
        if p.get("final_team"):
            team = db.teams.find_one({"_id": p.get("final_team")})
        
        data.append({
            "Player Name": p.get("name"),
            "Category": p.get("category"),
            "Base Price": p.get("base_price"),
            "Status": p.get("status"),
            "Final Bid": p.get("final_bid") if p.get("status") == "sold" else "N/A",
            "Team": team.get("name") if team else "N/A",
            "Affiliation": p.get("affiliation_role")
        })
    
    df = pd.DataFrame(data)
    
    if format == "excel":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Auction Summary')
        output.seek(0)
        
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=auction_summary_{datetime.now().strftime('%Y%m%d')}.xlsx"
            }
        )
    else:
        csv_data = df.to_csv(index=False)
        
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=auction_summary_{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )
