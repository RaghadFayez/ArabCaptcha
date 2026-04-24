"""
services/solve_service.py

Handles CAPTCHA solve attempts:
  - Trust Gate: verify reference word answer first
  - Record attempt
  - If trusted, store low-confidence submission for crowdsourcing
  - Issue token on success
"""
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import (
    Challenge, Attempt, ReferenceWord,
    LowConfidenceSubmission, BehaviorLog, SiteSession
)
from app.utils.text_normalizer import normalize_arabic, texts_match
from app.services.consensus_service import update_consensus
from app.utils.bot_scorer import calculate_bot_score
from app.core.config import settings


def solve_challenge(
    challenge_id: str,
    ref_answer: str,
    low_conf_answer: str,
    response_time_ms: float | None,
    signals_json: str | None,
    db: Session,
) -> dict:
    """
    Process a solve attempt:
      1. Validate challenge (exists, pending, not expired)
      2. Count existing attempts
      3. Check reference answer (Trust Gate)
      4. If correct → record low-confidence submission + update consensus
      5. Update challenge status
      6. Return result with token if passed
    """
    # ── Validate challenge ───────────────────────────────────────────────
    challenge = db.query(Challenge).filter(
        Challenge.challenge_id == challenge_id
    ).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge.status != "pending":
        raise HTTPException(status_code=400, detail="Challenge already resolved")
    if datetime.utcnow() > challenge.expires_at:
        challenge.status = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="Challenge has expired")

    # ── Count attempts ───────────────────────────────────────────────────
    attempt_count = db.query(Attempt).filter(
        Attempt.challenge_id == challenge_id
    ).count()

    if attempt_count >= challenge.max_attempts:
        challenge.status = "failed"
        db.commit()
        raise HTTPException(status_code=400, detail="Maximum attempts reached")

    # ── Trust Gate: check reference answer ───────────────────────────────
    ref_word = db.query(ReferenceWord).filter(
        ReferenceWord.word_id == challenge.ref_word_id
    ).first()

    ref_correct = texts_match(ref_answer, ref_word.correct_text)

    # ── Record the attempt ───────────────────────────────────────────────
    attempt = Attempt(
        challenge_id=challenge_id,
        attempt_number=attempt_count + 1,
        reference_input_text=ref_answer,
        reference_input_normalized=normalize_arabic(ref_answer),
        low_conf_input_text=low_conf_answer,
        low_conf_input_normalized=normalize_arabic(low_conf_answer),
        passed=ref_correct,
        response_time_ms=response_time_ms,
        signals_json=signals_json,
    )
    db.add(attempt)
    db.flush()

    # ── Log behavior signals ─────────────────────────────────────────────
    if signals_json:
        log = BehaviorLog(
            session_id=challenge.session_id,
            event_type="solve_attempt",
            signals_json=signals_json,
        )
        db.add(log)
        
        # ── Recalculate Bot Score ────────────────────────────────────────────
        current_bot_score = calculate_bot_score(signals_json)
        challenge.bot_score = current_bot_score
        
        # Keep session updated with the latest score for adaptive difficulty
        session = db.query(SiteSession).filter(SiteSession.session_id == challenge.session_id).first()
        if session:
            session.bot_score_final = current_bot_score

        # Hard Reject: Fail the challenge immediately if the final score indicates obvious bot behavior
        if current_bot_score >= settings.HIGH_RISK_THRESHOLD:
            ref_correct = False
            attempt.passed = False

    # ── If reference answer is correct → Trust Gate passed ───────────────
    token = None
    if ref_correct:
        # Store low-confidence submission for crowdsourcing
        submission = LowConfidenceSubmission(
            low_conf_word_id=challenge.low_conf_word_id,
            attempt_id=attempt.attempt_id,
            submitted_text=low_conf_answer,
            normalized_text=normalize_arabic(low_conf_answer),
        )
        db.add(submission)

        # Mark challenge as passed
        challenge.status = "passed"
        challenge.is_human_verified = True

        # Close the session to prevent reuse and secure the final bot score
        session_to_close = db.query(SiteSession).filter(SiteSession.session_id == challenge.session_id).first()
        if session_to_close:
            session_to_close.status = "completed"

        # Generate verification token
        token = str(uuid.uuid4())

        db.commit()

        # Update consensus (after commit so submission is persisted)
        update_consensus(challenge.low_conf_word_id, db)
    else:
        # Check if this was the last attempt
        if attempt_count + 1 >= challenge.max_attempts:
            challenge.status = "failed"
        db.commit()

    attempts_left = challenge.max_attempts - (attempt_count + 1)

    return {
        "passed": ref_correct,
        "attempts_left": max(attempts_left, 0),
        "token": token,
    }
