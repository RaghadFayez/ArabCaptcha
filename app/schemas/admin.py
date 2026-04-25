from pydantic import BaseModel
from datetime import datetime

class DashboardStats(BaseModel):
    total_sessions: int
    total_challenges: int
    bot_rate: float  # Percentage of sessions with risk_level 'high'
    solve_rate: float # Percentage of challenges with status 'passed'
    active_words: int

class RecentSession(BaseModel):
    session_id: str
    session_created_at: datetime
    bot_score_initial: float | None
    bot_score_final: float | None
    risk_level: str | None
    status: str

class RecentChallenge(BaseModel):
    challenge_id: str
    created_at: datetime
    difficulty: str
    status: str
    is_human_verified: bool
    bot_score: float | None
