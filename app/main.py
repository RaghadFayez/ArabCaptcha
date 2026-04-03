from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.routers import session, challenge, solve, ocr, admin

app = FastAPI(
    title="ArabCaptcha Backend API",
    description="Backend service for ArabCaptcha, providing endpoints for CAPTCHA generation, validation, and crowdsourcing.",
    version="1.0.0",
)

# Allow all origins for development. In production, this should be restricted.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount assets directory for rendering
assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "words")
if os.path.isdir(assets_dir):
    app.mount("/assets/words", StaticFiles(directory=assets_dir), name="word_images")

public_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
if os.path.isdir(public_dir):
    app.mount("/public", StaticFiles(directory=public_dir), name="public")

# Include all the API routers
app.include_router(session.router)
app.include_router(challenge.router)
app.include_router(solve.router)
app.include_router(ocr.router)
app.include_router(admin.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the ArabCaptcha API"}
