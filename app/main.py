from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# Include all the API routers
app.include_router(session.router)
app.include_router(challenge.router)
app.include_router(solve.router)
app.include_router(ocr.router)
app.include_router(admin.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the ArabCaptcha API"}
