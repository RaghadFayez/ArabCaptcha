"""
routers/ocr.py

API endpoint for ingesting words from the OCR pipeline.
Currently a stub — ready for when the OCR model is available.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.word import WordIngest, WordIngestResponse
from app.services.ocr_service import ingest_word

router = APIRouter(prefix="/words", tags=["OCR"])


@router.post("/ingest", response_model=WordIngestResponse)
def ingest_ocr_word(payload: WordIngest, db: Session = Depends(get_db)):
    """
    Add a new word to the system from the OCR pipeline.
    Supports both 'reference' and 'low_confidence' word types.
    """
    word = ingest_word(
        image_path=payload.image_path,
        word_type=payload.word_type,
        correct_text=payload.correct_text,
        source=payload.source,
        initial_confidence=payload.initial_confidence,
        db=db,
    )
    return WordIngestResponse(
        word_id=word.word_id,
        word_type=word.word_type,
    )
