"""Bid schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BidRequest(BaseModel):
    """Schema for placing a bid."""
    player_id: str
    team_id: str
    bid_amount: float = Field(..., gt=0)


class BidResponse(BaseModel):
    """Schema for bid response."""
    id: str
    player_id: str
    team_id: str
    bid_amount: float
    bidder_id: str
    timestamp: datetime
    is_winning: bool


class BidHistoryResponse(BaseModel):
    """Schema for bid history."""
    player_id: str
    player_name: str
    bids: list
    final_bid: Optional[float] = None
    winning_team: Optional[str] = None
