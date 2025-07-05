"""
Trackly FastAPI application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.databases.postgres import test_connection
from app.routes.user_routes import router as user_router
from app.routes.issue_routes import router as issue_router
from app.routes.file_routes import router as file_router
from app.routes.auth_routes import router as auth_router

# Create FastAPI app
app = FastAPI(
    title="Trackly API",
    description="Issues & Insights Tracker",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(user_router, prefix="/api")
app.include_router(issue_router, prefix="/api")
app.include_router(file_router, prefix="/api")
app.include_router(auth_router, prefix="/api")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    print("🚀 Starting Trackly API...")
    
    # Test database connection
    if test_connection():
        print("📋 Note: Use 'alembic upgrade head' to apply migrations")
    else:
        print("❌ Database connection failed")

# Root endpoint
@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Trackly API",
        "docs": "/docs",
        "version": "1.0.0",
        "migrations": "Use 'alembic upgrade head' to apply database migrations"
    }

# Health check
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)