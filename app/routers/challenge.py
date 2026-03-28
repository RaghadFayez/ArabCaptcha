"""
routers/challenge.py

API endpoints for creating and retrieving CAPTCHA challenges.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.challenge import ChallengeCreate, ChallengeResponse
from app.services.challenge_service import create_challenge, get_challenge, get_image_url

router = APIRouter(prefix="/challenges", tags=["Challenges"])


@router.post("", response_model=ChallengeResponse)
def request_challenge(payload: ChallengeCreate, db: Session = Depends(get_db)):
    """
    Request a new CAPTCHA challenge for an active session.
    Returns two word images (reference + low-confidence) and difficulty.
    """
    challenge = create_challenge(session_id=payload.session_id, db=db)
    return ChallengeResponse(
        challenge_id=challenge.challenge_id,
        ref_image_url=get_image_url(challenge.ref_word_id, db),
        low_conf_image_url=get_image_url(challenge.low_conf_word_id, db),
        difficulty=challenge.difficulty,
        expires_at=challenge.expires_at,
        max_attempts=challenge.max_attempts,
    )


@router.get("/{challenge_id}", response_model=ChallengeResponse)
def fetch_challenge(challenge_id: str, db: Session = Depends(get_db)):
    """Retrieve details of an existing challenge."""
    challenge = get_challenge(challenge_id=challenge_id, db=db)
    return ChallengeResponse(
        challenge_id=challenge.challenge_id,
        ref_image_url=get_image_url(challenge.ref_word_id, db),
        low_conf_image_url=get_image_url(challenge.low_conf_word_id, db),
        difficulty=challenge.difficulty,
        expires_at=challenge.expires_at,
        max_attempts=challenge.max_attempts,
    )
