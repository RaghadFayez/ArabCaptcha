"""
main.py

FastAPI application entry point.
Registers all routers and configures CORS + static file serving.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import traceback
import logging

logging.basicConfig(level=logging.DEBUG)

from app.db.session import engine, Base
from app.routers import session, challenge, solve, ocr, admin

# ── Create all tables (safe if they already exist) ───────────────────────
Base.metadata.create_all(bind=engine)

# ── App instance ─────────────────────────────────────────────────────────
app = FastAPI(
    title="ArabCaptcha API",
    description="Arabic CAPTCHA system with crowdsourced text digitization",
    version="1.0.0",
)

# ── CORS — allow all origins during development ─────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files for word images ─────────────────────────────────────────
assets_dir = os.path.join(os.path.dirname(__file__), "assets", "words")
if os.path.isdir(assets_dir):
    app.mount("/assets/words", StaticFiles(directory=assets_dir), name="word_images")

# ── Register routers ────────────────────────────────────────────────────
app.include_router(session.router)
app.include_router(challenge.router)
app.include_router(solve.router)
app.include_router(ocr.router)
app.include_router(admin.router)


@app.get("/", tags=["Health"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "ArabCaptcha"}


@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_str = "".join(tb)
    print(f"ERROR: {tb_str}", flush=True)
    return JSONResponse(status_code=500, content={"detail": str(exc), "traceback": tb_str})
