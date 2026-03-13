"""
Players router.
Handles player CRUD operations, image upload, and public registration.
"""
from fastapi import APIRouter, HTTPException, Depends, Form, Query, File, UploadFile
from typing import List, Optional
from datetime import datetime, timezone
from bson import ObjectId
import os
import uuid
from pathlib import Path

from database import db
from core.security import get_current_user, require_admin
from core.config import settings
from core.cloudinary_config import upload_image, delete_image, is_cloudinary_configured
from schemas.player import (
    PlayerCreate,
    PlayerUpdate,
    PlayerResponse,
    PlayerPublicRegister,
    SetBasePriceRequest
)

router = APIRouter(prefix="/players", tags=["Players"])

# Ensure upload directory exists (fallback for local storage)
UPLOAD_DIR = Path("static/uploads/players")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def serialize_player(doc: dict) -> dict:
    """Convert MongoDB document to API response format."""
    doc["_id"] = str(doc["_id"])
    
    # Get team name if player is assigned
    team_id = doc.get("final_team") or doc.get("current_team")
    if team_id:
        try:
            team = db.teams.find_one({"_id": ObjectId(team_id)})
            if team:
                doc["team_name"] = team.get("name")
        except Exception:
            pass
    
    return doc


@router.post("/upload-image/{player_id}")
async def upload_player_image(
    player_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload player image to Cloudinary or local storage."""
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPEG, PNG, and WebP are allowed."
        )
    
    # Validate file size (5MB max)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 5MB.")
    
    try:
        pid = ObjectId(player_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid player ID")
    
    player = db.players.find_one({"_id": pid})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    image_url = None
    
    # Try Cloudinary first, fallback to local storage
    if is_cloudinary_configured():
        # Upload to Cloudinary
        result = upload_image(contents, file.filename)
        if result.get("success"):
            image_url = result.get("url")
        else:
            raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {result.get('error')}")
    else:
        # Fallback to local storage
        file_ext = file.filename.split(".")[-1]
        unique_filename = f"{player_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
        file_path = UPLOAD_DIR / unique_filename
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        image_url = f"/static/uploads/players/{unique_filename}"
    
    # Update player with image path
    db.players.update_one(
        {"_id": pid},
        {"$set": {"image_path": image_url, "updated_at": datetime.now(timezone.utc)}}
    )
    
    return {"ok": True, "image_path": image_url}


@router.post("/public_register")
async def public_player_register(
    full_name: str = Form(...),
    role: str = Form(...),  # Playing position (Batsman, Bowler, etc.)
    category: Optional[str] = Form(None),  # Affiliation (Faculty, Student, Alumni)
    age: Optional[int] = Form(None),
    batting_style: Optional[str] = Form(None),
    bowling_style: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None)
):
    """Public endpoint for player self-registration with optional image."""
    name = (full_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Full name is required")
    
    # Validate role (playing position)
    allowed_roles = {"Batsman", "Bowler", "All-Rounder", "Wicketkeeper"}
    if not role or role not in allowed_roles:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid role. Must be one of: {', '.join(sorted(allowed_roles))}"
        )
    
    # Validate category (affiliation) - optional
    allowed_categories = {"Faculty", "Student", "Alumni"}
    if category and category not in allowed_categories:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid category. Must be one of: {', '.join(sorted(allowed_categories))}"
        )
    
    image_path = None
    cloudinary_status = "not_attempted"
    
    if photo and photo.filename:
        # Validate and save image
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        if photo.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid image type")
        
        contents = await photo.read()
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large. Maximum 5MB.")
        
        # Try Cloudinary first, fallback to local storage
        if is_cloudinary_configured():
            print(f"📤 Uploading to Cloudinary: {photo.filename}")
            cloudinary_status = "configured"
            result = upload_image(contents, photo.filename)
            if result.get("success"):
                image_path = result.get("url")
                cloudinary_status = "success"
                print(f"✅ Cloudinary upload successful: {image_path}")
            else:
                cloudinary_status = f"failed: {result.get('error')}"
                print(f"❌ Cloudinary upload failed: {result.get('error')}")
                # Don't fallback to local - Railway filesystem is ephemeral
                print(f"⚠️ Image not saved - Cloudinary required for Railway deployment")
        else:
            cloudinary_status = "not_configured"
            print(f"⚠️ Cloudinary not configured - image will not be saved")
            print(f"   Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET in Railway")
    
    player_doc = {
        "name": name,
        "role": role,
        "category": category or None,
        "age": age,
        "batting_style": (batting_style or "").strip(),
        "bowling_style": (bowling_style or "").strip(),
        "bio": (bio or "").strip(),
        "image_path": image_path,
        "base_price": None,
        "base_price_status": "pending",
        "status": "available",
        "is_approved": False,  # Requires admin approval
        "is_live": False,
        "auction_round": 1,
        "current_team": None,
        "final_team": None,
        "final_bid": None,
        "created_by": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    result = db.players.insert_one(player_doc)
    
    return {
        "ok": True,
        "player_id": str(result.inserted_id),
        "message": "Registration successful! Your profile is pending admin approval."
    }


@router.post("/add")
async def add_player(
    player: PlayerCreate,
    current_user: dict = Depends(require_admin)
):
    """Add a new player (Admin only)."""
    player_doc = player.dict()
    player_doc.update({
        "status": "available",
        "base_price_status": "set" if player.base_price else "pending",
        "auction_round": 1,
        "current_team": None,
        "final_team": None,
        "final_bid": None,
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    })
    
    result = db.players.insert_one(player_doc)
    
    return {"ok": True, "id": str(result.inserted_id)}


@router.get("/")
async def list_players(
    status: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    auction_round: Optional[int] = Query(None),
    include_unapproved: bool = Query(False)
):
    """List all players with optional filters and pagination.
    By default, only shows approved players unless include_unapproved=true."""
    query = {}
    
    # Filter by approval status (default: only approved)
    if not include_unapproved:
        query["is_approved"] = True
    
    if status:
        query["status"] = status
    
    if role:
        query["role"] = role
    
    if category:
        query["category"] = category
    
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    
    if auction_round:
        query["auction_round"] = auction_round
    
    # Calculate skip for pagination
    skip = (page - 1) * limit
    
    # Get total count
    total = db.players.count_documents(query)
    
    # Get players with pagination
    players = [
        serialize_player(p) 
        for p in db.players.find(query).skip(skip).limit(limit).sort("created_at", -1)
    ]
    
    return {
        "players": players,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


@router.get("/{player_id}")
async def get_player(player_id: str):
    """Get a specific player by ID."""
    try:
        player = db.players.find_one({"_id": ObjectId(player_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid player ID")
    
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return serialize_player(player)


@router.put("/update/{player_id}")
async def update_player(
    player_id: str,
    player: PlayerUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update a player (Admin only)."""
    try:
        pid = ObjectId(player_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid player ID")
    
    update_data = {k: v for k, v in player.dict(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    result = db.players.update_one(
        {"_id": pid},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return {"ok": True, "message": "Player updated"}


@router.delete("/delete/{player_id}")
async def delete_player(
    player_id: str,
    current_user: dict = Depends(require_admin)
):
    """Delete a player (Admin only)."""
    try:
        pid = ObjectId(player_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid player ID")
    
    # Get player to delete image if exists
    player = db.players.find_one({"_id": pid})
    if player and player.get("image_path"):
        try:
            image_file = Path("static" + player["image_path"].replace("/static", ""))
            if image_file.exists():
                image_file.unlink()
        except Exception:
            pass
    
    result = db.players.delete_one({"_id": pid})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return {"ok": True, "message": "Player deleted"}
