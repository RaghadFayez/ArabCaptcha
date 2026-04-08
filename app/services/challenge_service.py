"""
services/challenge_service.py

Creates CAPTCHA challenges by selecting words and setting difficulty.
"""
import random
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import SiteSession, Challenge, ReferenceWord, LowConfidenceWord, Word
from app.core.config import settings
from app.utils.bot_scorer import determine_difficulty


def create_challenge(session_id: str, db: Session) -> Challenge:
    """
    1. Verify session is active.
    2. Pick a random active reference word.
    3. Pick a random pending low-confidence word.
    4. Set difficulty from session's bot score.
    5. Create and return the Challenge.
    """
    # ── Validate session ─────────────────────────────────────────────────
    site_session = db.query(SiteSession).filter(
        SiteSession.session_id == session_id
    ).first()
    if not site_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if site_session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    # ── Pick reference word ──────────────────────────────────────────────
    ref_word = (
        db.query(ReferenceWord)
        .filter(ReferenceWord.active == True)
        .order_by(func.random())
        .first()
    )
    if not ref_word:
        raise HTTPException(status_code=503, detail="No reference words available")

    # ── Pick low-confidence word ─────────────────────────────────────────
    low_conf_word = (
        db.query(LowConfidenceWord)
        .filter(LowConfidenceWord.status == "pending")
        .order_by(func.random())
        .first()
    )
    if not low_conf_word:
        raise HTTPException(status_code=503, detail="No low-confidence words available")

    # ── Determine difficulty ─────────────────────────────────────────────
    bot_score = site_session.bot_score_final or site_session.bot_score_initial or 0.0
    difficulty = determine_difficulty(bot_score)

    # ── Create challenge ─────────────────────────────────────────────────
    challenge = Challenge(
        session_id=session_id,
        ref_word_id=ref_word.word_id,
        low_conf_word_id=low_conf_word.word_id,
        bot_score=bot_score,
        difficulty=difficulty,
        max_attempts=settings.MAX_CHALLENGE_ATTEMPTS,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.CHALLENGE_EXPIRY_MINUTES),
        status="pending",
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return challenge


def get_challenge(challenge_id: str, db: Session) -> Challenge:
    """Fetch a challenge by ID or 404."""
    challenge = db.query(Challenge).filter(
        Challenge.challenge_id == challenge_id
    ).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return challenge


def get_image_url(word_id: int, db: Session) -> str:
    """Get the image URL/path for a word."""
    word = db.query(Word).filter(Word.word_id == word_id).first()
    return word.image_path if word else ""
