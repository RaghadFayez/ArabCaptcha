"""
routers/solve.py

API endpoint for submitting CAPTCHA solve attempts.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.attempt import AttemptCreate, AttemptResponse
from app.services.solve_service import solve_challenge

router = APIRouter(prefix="/challenges", tags=["Solve"])


@router.post("/{challenge_id}/solve", response_model=AttemptResponse)
def submit_answer(challenge_id: str, payload: AttemptCreate, db: Session = Depends(get_db)):
    """
    Submit an answer for a challenge.

    The reference word answer is checked first (Trust Gate).
    If correct, the low-confidence answer is recorded for crowdsourcing.
    Returns a verification token on success.
    """
    result = solve_challenge(
        challenge_id=challenge_id,
        ref_answer=payload.ref_answer,
        low_conf_answer=payload.low_conf_answer,
        response_time_ms=payload.response_time_ms,
        signals_json=payload.signals_json,
        db=db,
    )
    return AttemptResponse(**result)
