"""
Trackly FastAPI application with background job scheduling
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.databases.postgres import test_connection
from app.routes.user_routes import router as user_router
from app.routes.issue_routes import router as issue_router
from app.routes.file_routes import router as file_router
from app.routes.auth_routes import router as auth_router
from app.routes.stats_routes import router as stats_router
from app.utils.scheduler import start_background_scheduler, stop_background_scheduler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting Trackly API...")

    # Test database connection
    if test_connection():
        logger.info("✅ Database connection successful")
        logger.info("📋 Note: Use 'alembic upgrade head' to apply migrations")
    else:
        logger.error("❌ Database connection failed")

    # Start background scheduler
    try:
        start_background_scheduler()
        logger.info("📊 Background scheduler started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start background scheduler: {str(e)}")

    logger.info("🎯 Trackly API startup complete")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Trackly API...")

    # Stop background scheduler
    try:
        stop_background_scheduler()
        logger.info("📊 Background scheduler stopped successfully")
    except Exception as e:
        logger.error(f"❌ Error stopping background scheduler: {str(e)}")

    logger.info("👋 Trackly API shutdown complete")


# Create FastAPI app with lifespan management
app = FastAPI(
    title="Trackly API",
    description="Issues & Insights Tracker with Background Job Processing",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(issue_router, prefix="/api")
app.include_router(file_router, prefix="/api")
app.include_router(stats_router, prefix="/api")  # New stats routes

# Root endpoint


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Trackly API",
        "docs": "/docs",
        "version": "1.0.0",
        "features": [
            "Issue tracking with RBAC",
            "File uploads to Azure Blob Storage",
            "Real-time SSE updates",
            "Background job scheduling",
            "Daily statistics aggregation"
        ],
        "migrations": "Use 'alembic upgrade head' to apply database migrations"
    }

# Health check


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2025-01-07T00:00:00Z",
        "services": {
            "api": "running",
            "scheduler": "check /api/stats/scheduler/status"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
