"""Auction schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AuctionStatus(BaseModel):
    """Schema for auction status."""
    active: bool
    current_player_id: Optional[str] = None
    current_player_name: Optional[str] = None
    timer_remaining: Optional[int] = None


class SetCurrentPlayerRequest(BaseModel):
    """Schema for setting current auction player."""
    player_id: str


class AuctionSessionCreate(BaseModel):
    """Schema for creating an auction session."""
    name: str = Field(..., min_length=1)
    description: Optional[str] = None


class AuctionSessionResponse(BaseModel):
    """Schema for auction session response."""
    id: str
    name: str
    description: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
