from pydantic import BaseModel, Field
from typing import List, Optional

class Artist(BaseModel):
    """Artist model with name and genres"""
    id: str
    name: str
    genres: List[str] = []

class PlaylistRequest(BaseModel):
    """Request model for playlist generation"""
    prompt: str = Field(..., description="Description of the desired playlist")
    model: str = Field(default="gpt-4", description="AI model to use")
    min_tracks: int = Field(default=30, ge=1, le=100, description="Minimum number of tracks")
    max_tracks: int = Field(default=50, ge=1, le=200, description="Maximum number of tracks")

class PlaylistResponse(BaseModel):
    name: str
    track_count: int
    artists: List[str]
    id: str | None = None  # Make ID optional

class AIRecommendation(BaseModel):
    """Model for AI recommendations"""
    artists: List[str]
    explanation: Optional[str] = None
