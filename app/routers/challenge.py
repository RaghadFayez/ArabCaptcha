"""
routers/challenge.py

API endpoints for creating and retrieving CAPTCHA challenges.
"""
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.challenge import ChallengeCreate, ChallengeResponse
from app.services.challenge_service import (
    create_challenge, get_challenge, get_image_url, get_word_image_path
)
from app.utils.image_obfuscation import apply_difficulty_filters, stitch_and_obfuscate

router = APIRouter(prefix="/challenges", tags=["Challenges"])


@router.post("", response_model=ChallengeResponse)
def request_challenge(payload: ChallengeCreate, db: Session = Depends(get_db)):
    """
    Request a new CAPTCHA challenge for an active session.
    Returns two dynamic image URLs (reference + low-confidence) and difficulty.
    """
    challenge = create_challenge(session_id=payload.session_id, db=db)
    return ChallengeResponse(
        challenge_id=challenge.challenge_id,
        ref_image_url=get_image_url(challenge.challenge_id, challenge.ref_word_id),
        low_conf_image_url=get_image_url(challenge.challenge_id, challenge.low_conf_word_id),
        composite_image_url=f"/challenges/{challenge.challenge_id}/image_composite",
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
        ref_image_url=get_image_url(challenge.challenge_id, challenge.ref_word_id),
        low_conf_image_url=get_image_url(challenge.challenge_id, challenge.low_conf_word_id),
        composite_image_url=f"/challenges/{challenge.challenge_id}/image_composite",
        difficulty=challenge.difficulty,
        expires_at=challenge.expires_at,
        max_attempts=challenge.max_attempts,
    )


from typing import Optional

@router.get("/{challenge_id}/image/{word_id}")
def serve_distorted_image(challenge_id: str, word_id: int, difficulty: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Serve a word image with difficulty-based visual distortion applied on-the-fly.
    'difficulty' can be passed as a query param for admin previews, 
    otherwise it's fetched from the challenge record.
    """
    # Use provided difficulty or fetch from challenge
    if not difficulty:
        challenge = get_challenge(challenge_id=challenge_id, db=db)
        difficulty = challenge.difficulty

    # Get raw image path
    raw_path = get_word_image_path(word_id=word_id, db=db)
    if not raw_path:
        raise HTTPException(status_code=404, detail="Word image not found")

    # Resolve absolute path (image_path may be relative like "assets/words/word1.jpg")
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    abs_path = os.path.join(base_dir, raw_path.lstrip("/"))

    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail=f"Image file not found: {raw_path}")

    # Read raw bytes
    with open(abs_path, "rb") as f:
        image_bytes = f.read()

    # Apply difficulty-based distortion
    distorted_bytes = apply_difficulty_filters(image_bytes, difficulty)

    return Response(content=distorted_bytes, media_type="image/jpeg")

@router.get("/{challenge_id}/image_composite")
def serve_composite_image(challenge_id: str, difficulty: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Serve a single stitched image containing both the reference and low-confidence words.
    Distortion is applied over the merged result to mask the boundary.
    """
    challenge = get_challenge(challenge_id=challenge_id, db=db)
    difficulty = difficulty or challenge.difficulty

    # Get raw image paths
    ref_path = get_word_image_path(word_id=challenge.ref_word_id, db=db)
    low_path = get_word_image_path(word_id=challenge.low_conf_word_id, db=db)

    if not ref_path or not low_path:
        raise HTTPException(status_code=404, detail="Word image not found")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    abs_ref_path = os.path.join(base_dir, ref_path.lstrip("/"))
    abs_low_path = os.path.join(base_dir, low_path.lstrip("/"))

    if not os.path.isfile(abs_ref_path) or not os.path.isfile(abs_low_path):
        raise HTTPException(status_code=404, detail="Image file missing from disk")

    with open(abs_ref_path, "rb") as f:
        ref_bytes = f.read()
    with open(abs_low_path, "rb") as f:
        low_bytes = f.read()

    # Apply stitching and difficulty-based distortion
    stitched_bytes = stitch_and_obfuscate(ref_bytes, low_bytes, difficulty)

    return Response(content=stitched_bytes, media_type="image/jpeg")
