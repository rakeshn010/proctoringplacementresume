"""
Teams router - Clean implementation.
Handles team CRUD operations with proper MongoDB integration.
"""
from fastapi import APIRouter, HTTPException, Depends, Form, File, UploadFile, status
from typing import List, Optional
from datetime import datetime, timezone
from bson import ObjectId
import logging

from database import db
from core.security import get_current_user, require_admin, hash_password
from websocket.manager import manager

router = APIRouter(prefix="/teams", tags=["Teams"])
logger = logging.getLogger(__name__)


@router.get("/")
async def list_teams():
    """List all teams with statistics."""
    try:
        teams = list(db.teams.find())
        result = []
        
        for team in teams:
            team_id = str(team["_id"])
            
            # Calculate statistics
            players = list(db.players.find({"final_team": team_id, "status": "sold"}))
            total_spent = sum(p.get("final_bid", 0) for p in players)
            players_count = len(players)
            highest_purchase = max([p.get("final_bid", 0) for p in players], default=0)
            
            result.append({
                "_id": team_id,
                "name": team.get("name"),
                "username": team.get("username"),
                "logo_path": team.get("logo_path", ""),
                "budget": team.get("budget", 0),
                "total_spent": total_spent,
                "remaining_budget": team.get("budget", 0) - total_spent,
                "players_count": players_count,
                "highest_purchase": highest_purchase,
                "created_at": team.get("created_at"),
                "updated_at": team.get("updated_at")
            })
        
        return result
    except Exception as e:
        logger.error(f"Error listing teams: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}")
async def get_team(team_id: str):
    """Get a specific team by ID."""
    try:
        team = db.teams.find_one({"_id": ObjectId(team_id)})
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        team_id_str = str(team["_id"])
        players = list(db.players.find({"final_team": team_id_str, "status": "sold"}))
        total_spent = sum(p.get("final_bid", 0) for p in players)
        highest_purchase = max([p.get("final_bid", 0) for p in players], default=0)
        
        return {
            "_id": team_id_str,
            "name": team.get("name"),
            "username": team.get("username"),
            "logo_path": team.get("logo_path", ""),
            "budget": team.get("budget", 0),
            "total_spent": total_spent,
            "remaining_budget": team.get("budget", 0) - total_spent,
            "players_count": len(players),
            "highest_purchase": highest_purchase,
            "players": [
                {
                    "_id": str(p["_id"]),
                    "name": p.get("name"),
                    "role": p.get("role"),
                    "category": p.get("category"),
                    "final_bid": p.get("final_bid"),
                    "image_path": p.get("image_path")
                }
                for p in players
            ]
        }
    except Exception as e:
        logger.error(f"Error getting team {team_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_team(
    name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    budget: float = Form(...),
    logo_path: str = Form(""),
    current_user: dict = Depends(require_admin)
):
    """Create a new team (Admin only)."""
    try:
        logger.info(f"Admin {current_user.get('email')} creating team: {name}")
        
        # Validate inputs
        if not name or not username or not password:
            raise HTTPException(status_code=400, detail="Name, username, and password are required")
        
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        if budget < 0:
            raise HTTPException(status_code=400, detail="Budget cannot be negative")
        
        username = username.strip().lower()
        
        # Check for duplicate username
        existing = db.teams.find_one({"username": username})
        if existing:
            raise HTTPException(status_code=400, detail=f"Username '{username}' already exists")
        
        # Create team document
        team_doc = {
            "name": name.strip(),
            "username": username,
            "hashed_password": hash_password(password),
            "budget": float(budget),
            "logo_path": logo_path.strip() if logo_path else "",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Insert into database
        result = db.teams.insert_one(team_doc)
        team_id = str(result.inserted_id)
        
        logger.info(f"Team created successfully: {name} (ID: {team_id})")
        
        # Broadcast team update to all clients
        await manager.broadcast_team_update({
            "team_id": team_id,
            "team_name": name,
            "action": "created",
            "budget": float(budget)
        })
        
        return {
            "ok": True,
            "id": team_id,
            "message": f"Team '{name}' created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating team: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create team: {str(e)}")


@router.put("/update/{team_id}")
async def update_team(
    team_id: str,
    name: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    budget: Optional[float] = Form(None),
    logo_path: Optional[str] = Form(None),
    current_user: dict = Depends(require_admin)
):
    """Update a team (Admin only)."""
    try:
        logger.info(f"Admin {current_user.get('email')} updating team: {team_id}")
        
        # Validate team ID
        try:
            tid = ObjectId(team_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid team ID")
        
        # Check if team exists
        team = db.teams.find_one({"_id": tid})
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Build update document
        update_data = {}
        
        if name:
            update_data["name"] = name.strip()
        
        if username:
            username = username.strip().lower()
            # Check for duplicate username (excluding current team)
            existing = db.teams.find_one({"username": username, "_id": {"$ne": tid}})
            if existing:
                raise HTTPException(status_code=400, detail=f"Username '{username}' already exists")
            update_data["username"] = username
        
        if password:
            if len(password) < 6:
                raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
            update_data["hashed_password"] = hash_password(password)
        
        if budget is not None:
            if budget < 0:
                raise HTTPException(status_code=400, detail="Budget cannot be negative")
            
            # Calculate total spent
            players = list(db.players.find({"final_team": team_id, "status": "sold"}))
            total_spent = sum(p.get("final_bid", 0) for p in players)
            
            if budget < total_spent:
                raise HTTPException(
                    status_code=400,
                    detail=f"Budget cannot be less than total spent (₹{total_spent})"
                )
            
            update_data["budget"] = float(budget)
        
        if logo_path is not None:
            update_data["logo_path"] = logo_path.strip()
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Add updated timestamp
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        # Update in database
        result = db.teams.update_one({"_id": tid}, {"$set": update_data})
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Team not found")
        
        logger.info(f"Team updated successfully: {team_id}")
        
        # Broadcast team update to all clients
        updated_team = db.teams.find_one({"_id": tid})
        await manager.broadcast_team_update({
            "team_id": team_id,
            "team_name": updated_team.get("name"),
            "action": "updated",
            "budget": updated_team.get("budget")
        })
        
        return {
            "ok": True,
            "message": "Team updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating team: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update team: {str(e)}")


@router.delete("/delete/{team_id}")
async def delete_team(
    team_id: str,
    current_user: dict = Depends(require_admin)
):
    """Delete a team (Admin only)."""
    try:
        logger.info(f"Admin {current_user.get('email')} deleting team: {team_id}")
        
        # Validate team ID
        try:
            tid = ObjectId(team_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid team ID")
        
        # Check if team has purchased players
        players = list(db.players.find({"final_team": team_id, "status": "sold"}))
        if players:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete team with {len(players)} purchased players. Remove players first."
            )
        
        # Delete team
        result = db.teams.delete_one({"_id": tid})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Team not found")
        
        logger.info(f"Team deleted successfully: {team_id}")
        
        # Broadcast team update to all clients
        await manager.broadcast_team_update({
            "team_id": team_id,
            "action": "deleted"
        })
        
        return {
            "ok": True,
            "message": "Team deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting team: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete team: {str(e)}")



@router.post("/upload-logo/{team_id}")
async def upload_team_logo(
    team_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin)
):
    """Upload team logo to Cloudinary."""
    from fastapi import File, UploadFile
    from core.cloudinary_config import upload_image, is_cloudinary_configured
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPEG, PNG, WebP, and SVG are allowed."
        )
    
    # Validate file size (2MB max for logos)
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 2MB.")
    
    try:
        tid = ObjectId(team_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid team ID")
    
    team = db.teams.find_one({"_id": tid})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    logo_url = None
    
    if is_cloudinary_configured():
        # Upload to Cloudinary
        result = upload_image(contents, file.filename, folder="cricket_auction/team_logos")
        if result.get("success"):
            logo_url = result.get("url")
        else:
            raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {result.get('error')}")
    else:
        raise HTTPException(status_code=500, detail="Cloudinary not configured")
    
    # Update team with logo path
    db.teams.update_one(
        {"_id": tid},
        {"$set": {"logo_path": logo_url, "updated_at": datetime.now(timezone.utc)}}
    )
    
    return {"ok": True, "logo_path": logo_url}
