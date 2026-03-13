"""Team schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class TeamBase(BaseModel):
    """Base team schema."""
    name: str = Field(..., min_length=1, max_length=100)
    budget: float = Field(..., ge=0)
    owner: Optional[str] = None


class TeamCreate(TeamBase):
    """Schema for creating a team."""
    pass


class TeamUpdate(BaseModel):
    """Schema for updating a team."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    budget: Optional[float] = Field(None, ge=0)
    owner: Optional[str] = None


class TeamResponse(TeamBase):
    """Schema for team response."""
    id: str
    players_count: int = 0
    total_spent: float = 0
    remaining_budget: float = 0
    created_at: datetime


class TeamDetailResponse(TeamResponse):
    """Schema for detailed team response with players."""
    players: List[dict] = []
