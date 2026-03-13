"""Player schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PlayerBase(BaseModel):
    """Base player schema."""
    name: str = Field(..., min_length=1, max_length=100)
    role: Optional[str] = Field(None, description="Batsman, Bowler, All-Rounder, Wicketkeeper")
    category: Optional[str] = Field(None, description="Faculty, Student, Alumni")
    age: Optional[int] = Field(None, ge=10, le=60)
    batting_style: Optional[str] = None
    bowling_style: Optional[str] = None
    bio: Optional[str] = None
    image_path: Optional[str] = None


class PlayerCreate(PlayerBase):
    """Schema for creating a player."""
    base_price: Optional[float] = Field(None, ge=0)


class PlayerPublicRegister(PlayerBase):
    """Schema for public player registration."""
    pass


class PlayerUpdate(BaseModel):
    """Schema for updating a player."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = None
    age: Optional[int] = Field(None, ge=10, le=60)
    batting_style: Optional[str] = None
    bowling_style: Optional[str] = None
    bio: Optional[str] = None
    base_price: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None


class PlayerResponse(PlayerBase):
    """Schema for player response."""
    id: str
    base_price: Optional[float] = None
    status: str
    final_bid: Optional[float] = None
    final_team: Optional[str] = None
    team_name: Optional[str] = None
    auction_round: int = 1
    created_at: datetime


class SetBasePriceRequest(BaseModel):
    """Schema for setting player base price."""
    price: float = Field(..., gt=0)
