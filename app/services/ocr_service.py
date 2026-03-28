"""
services/ocr_service.py

Stub service for OCR word ingestion.
Ready to connect to an actual OCR model in the future.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import Word, ReferenceWord, LowConfidenceWord


def ingest_word(
    image_path: str,
    word_type: str,
    correct_text: str | None,
    source: str | None,
    initial_confidence: float | None,
    db: Session,
) -> Word:
    """
    Add a new word to the system:
      - If word_type == "reference": create Word + ReferenceWord (correct_text required)
      - If word_type == "low_confidence": create Word + LowConfidenceWord
    """
    if word_type not in ("reference", "low_confidence"):
        raise HTTPException(status_code=400, detail="word_type must be 'reference' or 'low_confidence'")

    if word_type == "reference" and not correct_text:
        raise HTTPException(status_code=400, detail="correct_text is required for reference words")

    # ── Create base word ─────────────────────────────────────────────────
    word = Word(image_path=image_path, word_type=word_type)
    db.add(word)
    db.flush()

    # ── Create subtype record ────────────────────────────────────────────
    if word_type == "reference":
        ref = ReferenceWord(
            word_id=word.word_id,
            correct_text=correct_text,
            source=source,
            active=True,
        )
        db.add(ref)
    else:
        lc = LowConfidenceWord(
            word_id=word.word_id,
            initial_confidence=initial_confidence,
            status="pending",
        )
        db.add(lc)

    db.commit()
    db.refresh(word)
    return word
