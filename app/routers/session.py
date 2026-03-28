"""
routers/session.py

API endpoints for session management.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.session import SessionCreate, SessionResponse
from app.services.session_service import create_session

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("", response_model=SessionResponse)
def create_new_session(payload: SessionCreate, db: Session = Depends(get_db)):
    """
    Create a new CAPTCHA session.

    Requires the client's API key and origin domain.
    Optionally accepts behavioral signals for initial bot score.
    """
    site_session = create_session(
        api_key=payload.api_key,
        domain=payload.domain,
        signals_json=payload.signals_json,
        db=db,
    )
    return SessionResponse(
        session_id=site_session.session_id,
        risk_level=site_session.risk_level or "low",
        bot_score=site_session.bot_score_initial or 0.0,
    )
