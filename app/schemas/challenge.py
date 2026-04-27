"""
schemas/challenge.py

Pydantic models for challenge-related API requests and responses.
"""
from datetime import datetime
from pydantic import BaseModel, Field


class ChallengeCreate(BaseModel):
    """POST /challenges — request a new CAPTCHA challenge."""
    session_id: str = Field(..., description="Active session ID")


from typing import Optional

class ChallengeResponse(BaseModel):
    """Response containing challenge details and image URLs."""
    challenge_id: str
    ref_image_url: str
    low_conf_image_url: str
    composite_image_url: Optional[str] = None
    difficulty: str
    expires_at: datetime
    max_attempts: int

    class Config:
        from_attributes = True
