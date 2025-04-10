from app.core.scheduler import setup_scheduler
from app.core.config import settings
from app.api.routes import documents, health, analytics, notifications, summaries, hierarchical_summaries
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import logging
import sys

# Configure logging to output to console
logging.basicConfig(
    stream=sys.stdout,  # Output to console
    level=logging.INFO,
    format='%(message)s'  # Simplified format for clearer debug output
)


app = FastAPI(
    title="Striim CS Backend",
    description="RAG Application Backend",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(
    analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(notifications.router, prefix="/api/v1",
                   tags=["notifications"])
app.include_router(summaries.router, prefix="/api/v1", tags=["summaries"])
app.include_router(
    hierarchical_summaries.router,
    prefix="/api/v1",
    tags=["summaries"]
)

# Setup scheduler
setup_scheduler(app)
