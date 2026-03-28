"""
services/session_service.py

Handles session creation: validates API key, computes bot score,
determines risk level, and persists the session.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import ClientSite, ClientDomain, SiteSession, BehaviorLog
from app.utils.hashing import hash_api_key
from app.utils.bot_scorer import calculate_bot_score, determine_risk_level


def create_session(
    api_key: str,
    domain: str,
    signals_json: str | None,
    db: Session,
) -> SiteSession:
    """
    1. Hash the API key and look up the client site.
    2. Verify the domain is allowed.
    3. Calculate initial bot score from signals.
    4. Create and return a SiteSession.
    """
    # ── Validate API key ──────────────────────────────────────────────────
    key_hash = hash_api_key(api_key)
    site = db.query(ClientSite).filter(ClientSite.api_key_hash == key_hash).first()
    if not site:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if site.status != "active":
        raise HTTPException(status_code=403, detail="Site is inactive")

    # ── Validate domain ──────────────────────────────────────────────────
    allowed = db.query(ClientDomain).filter(
        ClientDomain.site_id == site.site_id,
        ClientDomain.domain_url == domain,
    ).first()
    if not allowed:
        raise HTTPException(status_code=403, detail="Domain not authorized")

    # ── Bot score ────────────────────────────────────────────────────────
    bot_score = calculate_bot_score(signals_json)
    risk_level = determine_risk_level(bot_score)

    # ── Create session ───────────────────────────────────────────────────
    session = SiteSession(
        site_id=site.site_id,
        bot_score_initial=bot_score,
        risk_level=risk_level,
        status="active",
    )
    db.add(session)
    db.flush()  # ensure session_id is generated before referencing it

    # ── Log behavior signals ─────────────────────────────────────────────
    if signals_json:
        log = BehaviorLog(
            session_id=session.session_id,
            event_type="session_init",
            signals_json=signals_json,
        )
        db.add(log)

    db.commit()
    db.refresh(session)
    return session
