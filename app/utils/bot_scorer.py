"""
utils/bot_scorer.py

Calculates a bot suspicion score (0–100) from behavioral signals.
Uses configurable weights from config.py.
"""
import json
from app.core.config import settings


def calculate_bot_score(signals_json: str | None) -> float:
    """
    Analyze behavior signals and return a bot score (0–100).

    Expected signals_json keys:
      - submit_time_ms: int      (time from page load to form submit)
      - paste_used: bool          (user pasted the answer)
      - mouse_moves: int          (number of mouse move events)
      - scroll_events: int        (number of scroll events)
      - webdriver: bool           (navigator.webdriver flag)
      - first_interaction_ms: int (time to first keystroke/click)
      - focus_blur_count: int     (number of tab switches)
      - failed_attempts: int      (previous failed attempts count)
    """
    if not signals_json:
        return 0.0

    try:
        signals = json.loads(signals_json) if isinstance(signals_json, str) else signals_json
    except (json.JSONDecodeError, TypeError):
        return 0.0

    score = 0.0

    # Fast submit (< 800ms)
    submit_time = signals.get("submit_time_ms", 5000)
    if submit_time < 800:
        score += settings.WEIGHT_FAST_SUBMIT

    # Paste used
    if signals.get("paste_used", False):
        score += settings.WEIGHT_PASTE_USED

    # No mouse movement AND no scroll
    mouse_moves = signals.get("mouse_moves", 1)
    scroll_events = signals.get("scroll_events", 1)
    if mouse_moves == 0 and scroll_events == 0:
        score += settings.WEIGHT_NO_MOUSE

    # Webdriver detected
    if signals.get("webdriver", False):
        score += settings.WEIGHT_WEBDRIVER

    # First interaction too fast (< 150ms)
    first_interaction = signals.get("first_interaction_ms", 500)
    if first_interaction < 150:
        score += settings.WEIGHT_FAST_FIRST_INTERACTION

    # Excessive tab switching (> 3 times)
    focus_blur = signals.get("focus_blur_count", 0)
    if focus_blur > 3:
        score += settings.WEIGHT_FOCUS_BLUR

    # Too many failed attempts (>= 3)
    failed_attempts = signals.get("failed_attempts", 0)
    if failed_attempts >= 3:
        score += settings.WEIGHT_TOO_MANY_ATTEMPTS

    return min(score, 100.0)


def determine_risk_level(bot_score: float) -> str:
    """Map a bot score to a risk level: low / med / high."""
    if bot_score < settings.LOW_RISK_THRESHOLD:
        return "low"
    elif bot_score < settings.HIGH_RISK_THRESHOLD:
        return "med"
    else:
        return "high"


def determine_difficulty(bot_score: float) -> str:
    """Map a bot score to challenge difficulty: easy / medium / hard."""
    if bot_score < settings.LOW_RISK_THRESHOLD:
        return "easy"
    elif bot_score < settings.HIGH_RISK_THRESHOLD:
        return "medium"
    else:
        return "hard"
