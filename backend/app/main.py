from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from .core.config import config
from .database import Base, engine
from .routers import digest, events, news, stats, travel

# Create DB tables
Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title=config.PROJECT_NAME, version=config.VERSION)
# Run with uvicorn app.main:app --reload

# Setup Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ORIGINS.split(','),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(events.router, prefix="/api/events", tags=["Events"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(travel.router, prefix="/api/travel", tags=["Travel"])
app.include_router(stats.router, prefix="/api/stats", tags=["Statistics"])
app.include_router(digest.router, prefix="/api/digest", tags=["Digest"])


@app.on_event("startup")
async def on_startup():
    # Start background tasks
    pass
    # start_scheduler()


@app.get("/")
@app.get("/api/health")
async def health_check():
    # Check DB connectivity
    db_status = "unknown"
    try:
        # Use a lightweight connection check
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)[:200]}"

    return {
        "message": config.PROJECT_NAME,
        "version": config.VERSION,
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": db_status,
            "scheduler": "running",
        },
    }
