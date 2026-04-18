"""
core/config.py

This file holds all application settings.
Change values here to tune the system behavior without touching any logic code.
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    # SQLite (development). To switch to MySQL, change to:
    # "mysql+pymysql://user:password@localhost/arabcaptcha"
    DATABASE_URL: str = "sqlite:///./arabcaptcha.db"

    @field_validator("DATABASE_URL")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        # SQLAlchemy 1.4+ removed support for "postgres://", requires "postgresql://"
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    # ── Bot Score Thresholds ─────────────────────────────────────────────────
    # Score is 0-100. Higher = more suspicious.
    # Scores below LOW_RISK_THRESHOLD → Easy CAPTCHA
    # Scores between LOW and HIGH    → Medium CAPTCHA
    # Scores above HIGH_RISK_THRESHOLD → Hard/Rejected CAPTCHA
    LOW_RISK_THRESHOLD: int = 25
    HIGH_RISK_THRESHOLD: int = 70

    # ── Bot Score Signal Weights ──────────────────────────────────────────────
    # Points added to the bot score when each suspicious signal is detected.
    # Increase a weight to be stricter about that signal.
    WEIGHT_FAST_SUBMIT: int = 35      # Submitted in < 800ms
    WEIGHT_PASTE_USED: int = 25       # Answer was pasted, not typed
    WEIGHT_NO_MOUSE: int = 25         # Zero mouse moves AND zero scrolls
    WEIGHT_WEBDRIVER: int = 90        # Browser is controlled by automation (Selenium, etc.)
    WEIGHT_FAST_FIRST_INTERACTION: int = 15  # First keystroke/click in < 150ms
    WEIGHT_FOCUS_BLUR: int = 10       # Switched tabs > 3 times
    WEIGHT_TOO_MANY_ATTEMPTS: int = 15  # Failed the challenge >= 3 times
    WEIGHT_KEYBOARD_ONLY: int = 20
    WEIGHT_FAST_START: int = 20

    # ── Consensus (Crowdsourcing) Settings ───────────────────────────────────
    # Minimum number of trusted votes before we evaluate a low-confidence word.
    MIN_VOTES_REQUIRED_FOR_CONSENSUS: int = 10

    # What fraction of votes must agree on the same text to accept it as correct.
    # e.g. 0.70 means 70% must agree.
    CONSENSUS_AGREEMENT_RATIO: float = 0.70

    # If a word gets this many attempts and still has no consensus, mark it as unreadable.
    MAX_ATTEMPTS_BEFORE_DISCARD: int = 50

    # ── Challenge Settings ───────────────────────────────────────────────────
    # How many minutes before an unsolved challenge expires.
    CHALLENGE_EXPIRY_MINUTES: int = 3

    # Maximum number of solve attempts allowed per challenge.
    MAX_CHALLENGE_ATTEMPTS: int = 3

    class Config:
        env_file = ".env"          # Optional: override any value via a .env file
        extra = "ignore"


# A single shared instance used across the entire application.
settings = Settings()
