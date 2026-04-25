"""
routers/admin.py

Admin endpoints for managing words and viewing consensus data.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Word, ReferenceWord, LowConfidenceWord, LowConfidenceConsensus, SiteSession, Challenge
from app.schemas.word import WordListItem, ConsensusDetail
from app.schemas.admin import DashboardStats, RecentSession, RecentChallenge

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/words", response_model=list[WordListItem])
def list_words(db: Session = Depends(get_db)):
    """List all words in the system (reference + low-confidence)."""
    words = db.query(Word).all()
    result = []
    for w in words:
        item = WordListItem(
            word_id=w.word_id,
            image_path=w.image_path,
            word_type=w.word_type,
            added_at=w.added_at,
        )
        if w.word_type == "reference":
            ref = db.query(ReferenceWord).filter(ReferenceWord.word_id == w.word_id).first()
            if ref:
                item.correct_text = ref.correct_text
                item.active = ref.active
        elif w.word_type == "low_confidence":
            lc = db.query(LowConfidenceWord).filter(LowConfidenceWord.word_id == w.word_id).first()
            if lc:
                item.status = lc.status
                item.verified_text = lc.verified_text
                item.total_votes = lc.total_votes
        result.append(item)
    return result


@router.patch("/words/{word_id}/activate")
def toggle_word_activation(word_id: int, active: bool = True, db: Session = Depends(get_db)):
    """Activate or deactivate a reference word."""
    ref = db.query(ReferenceWord).filter(ReferenceWord.word_id == word_id).first()
    if not ref:
        raise HTTPException(status_code=404, detail="Reference word not found")
    ref.active = active
    db.commit()
    return {"word_id": word_id, "active": active}


@router.get("/words/{word_id}/consensus", response_model=ConsensusDetail)
def get_word_consensus(word_id: int, db: Session = Depends(get_db)):
    """Get consensus details for a low-confidence word."""
    consensus = db.query(LowConfidenceConsensus).filter(
        LowConfidenceConsensus.low_conf_word_id == word_id
    ).first()
    if not consensus:
        raise HTTPException(status_code=404, detail="No consensus data for this word")
    return ConsensusDetail(
        low_conf_word_id=consensus.low_conf_word_id,
        top_candidate_text=consensus.top_candidate_text,
        votes=consensus.votes,
        total=consensus.total,
        ratio=consensus.ratio,
        is_verified=consensus.is_verified,
    )


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Aggregate stats for the admin dashboard."""
    total_sessions = db.query(SiteSession).count()
    total_challenges = db.query(Challenge).count()
    bot_sessions = db.query(SiteSession).filter(SiteSession.risk_level == "high").count()
    passed_challenges = db.query(Challenge).filter(Challenge.status == "passed").count()
    active_words = db.query(ReferenceWord).filter(ReferenceWord.active == True).count()
    
    bot_rate = (bot_sessions / total_sessions * 100) if total_sessions > 0 else 0
    solve_rate = (passed_challenges / total_challenges * 100) if total_challenges > 0 else 0
    
    return DashboardStats(
        total_sessions=total_sessions,
        total_challenges=total_challenges,
        bot_rate=round(bot_rate, 2),
        solve_rate=round(solve_rate, 2),
        active_words=active_words
    )


@router.get("/recent-sessions", response_model=list[RecentSession])
def list_recent_sessions(db: Session = Depends(get_db)):
    """Fetch recent sessions for the dashboard."""
    return db.query(SiteSession).order_by(SiteSession.session_created_at.desc()).limit(50).all()


@router.get("/recent-challenges", response_model=list[RecentChallenge])
def list_recent_challenges(db: Session = Depends(get_db)):
    """Fetch recent challenges for the dashboard."""
    return db.query(Challenge).order_by(Challenge.created_at.desc()).limit(50).all()
