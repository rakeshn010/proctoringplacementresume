"""
Chat and messaging router.
Handles team chat, private messages, and group discussions.
"""
from fastapi import APIRouter, HTTPException, Depends, Form
from typing import List, Optional
from bson import ObjectId
from datetime import datetime, timezone

from database import db
from core.security import get_current_user
from websocket.manager import manager

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/send")
async def send_message(
    message: str = Form(...),
    room: str = Form("global"),
    current_user: dict = Depends(get_current_user)
):
    """Send a chat message."""
    try:
        # Create message document
        msg_doc = {
            "user_id": current_user.get("user_id"),
            "user_email": current_user.get("email"),
            "team_id": current_user.get("team_id"),
            "message": message,
            "room": room,
            "timestamp": datetime.now(timezone.utc),
            "edited": False,
            "deleted": False
        }
        
        # Get user/team name
        if current_user.get("is_admin"):
            msg_doc["sender_name"] = "Admin"
            msg_doc["sender_type"] = "admin"
        elif current_user.get("team_id"):
            team = db.teams.find_one({"_id": ObjectId(current_user.get("team_id"))})
            msg_doc["sender_name"] = team.get("name", "Unknown Team") if team else "Unknown Team"
            msg_doc["sender_type"] = "team"
        else:
            msg_doc["sender_name"] = current_user.get("email", "Unknown")
            msg_doc["sender_type"] = "user"
        
        # Insert message
        result = db.chat_messages.insert_one(msg_doc)
        msg_doc["_id"] = str(result.inserted_id)
        
        # Broadcast message via WebSocket
        await manager.broadcast({
            "type": "chat_message",
            "data": {
                "id": str(result.inserted_id),
                "sender_name": msg_doc["sender_name"],
                "sender_type": msg_doc["sender_type"],
                "message": message,
                "room": room,
                "timestamp": msg_doc["timestamp"].isoformat()
            }
        })
        
        return {
            "ok": True,
            "message_id": str(result.inserted_id),
            "message": "Message sent successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")


@router.get("/messages")
async def get_messages(
    room: str = "global",
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get chat messages for a room."""
    try:
        messages = list(
            db.chat_messages.find({
                "room": room,
                "deleted": False
            })
            .sort("timestamp", -1)
            .limit(limit)
        )
        
        # Convert ObjectId to string and format
        for msg in messages:
            msg["_id"] = str(msg["_id"])
            if msg.get("timestamp"):
                msg["timestamp"] = msg["timestamp"].isoformat()
        
        # Reverse to show oldest first
        messages.reverse()
        
        return {
            "ok": True,
            "messages": messages,
            "count": len(messages)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting messages: {str(e)}")


@router.delete("/message/{message_id}")
async def delete_message(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a message (only own messages or admin)."""
    try:
        mid = ObjectId(message_id)
        message = db.chat_messages.find_one({"_id": mid})
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Check permission
        is_owner = message.get("user_id") == current_user.get("user_id")
        is_admin = current_user.get("is_admin", False)
        
        if not (is_owner or is_admin):
            raise HTTPException(status_code=403, detail="Not authorized to delete this message")
        
        # Mark as deleted
        db.chat_messages.update_one(
            {"_id": mid},
            {"$set": {"deleted": True, "deleted_at": datetime.now(timezone.utc)}}
        )
        
        # Broadcast deletion
        await manager.broadcast({
            "type": "chat_message_deleted",
            "data": {"message_id": message_id}
        })
        
        return {"ok": True, "message": "Message deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting message: {str(e)}")


@router.get("/rooms")
async def get_chat_rooms(current_user: dict = Depends(get_current_user)):
    """Get available chat rooms."""
    rooms = [
        {"id": "global", "name": "Global Chat", "description": "Chat with all teams"},
        {"id": "admin", "name": "Admin Announcements", "description": "Official announcements"}
    ]
    
    # Add team-specific room if user has a team
    if current_user.get("team_id"):
        team = db.teams.find_one({"_id": ObjectId(current_user.get("team_id"))})
        if team:
            rooms.append({
                "id": f"team_{current_user.get('team_id')}",
                "name": f"{team.get('name')} Team Chat",
                "description": "Private team discussion"
            })
    
    return {"ok": True, "rooms": rooms}
