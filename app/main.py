import os
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from app.db.session import engine, Base

from app.routers import session, challenge, solve, ocr, admin

# ── Create all tables (safe if they already exist) ───────────────────────
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ArabCaptcha Backend API",
    description="Backend service for ArabCaptcha, providing endpoints for CAPTCHA generation, validation, and crowdsourcing.",
    version="1.0.0",
)

# Allow all origins for development. In production, this should be restricted.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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

# No need for redirect anymore as it's /public again

# Include all the API routers
app.include_router(session.router)
app.include_router(challenge.router)
app.include_router(solve.router)
app.include_router(ocr.router)
app.include_router(admin.router)

@app.get("/")
def read_root():
    admin_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public", "admin.html")
    if os.path.isfile(admin_path):
        return FileResponse(admin_path, media_type="text/html")
    return {"message": "Welcome to the ArabCaptcha API"}

@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_str = "".join(tb)
    print(f"ERROR: {tb_str}", flush=True)
    return JSONResponse(status_code=500, content={"detail": str(exc), "traceback": tb_str})
