"""Main FastAPI application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.services.data_loader import initialize_data
from app.routes import walkability, environmental, pathfinding, profile, chat, search
from app.analysis.pathfinding import initialize_pathfinder

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS
)

# Include routers
app.include_router(walkability.router)
app.include_router(environmental.router)
app.include_router(pathfinding.router)
app.include_router(profile.router)
app.include_router(chat.router)
app.include_router(search.router)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # Load geospatial data
    print("📊 Loading geospatial data...")
    initialize_data()
    print("✅ Data loaded successfully")
    
    # Initialize pathfinding system
    print("🗺️  Initializing pathfinding system...")
    success = initialize_pathfinder()
    if success:
        print("✅ Pathfinding system initialized successfully")
    else:
        print("⚠️  Warning: Pathfinding system failed to initialize")


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": f"{settings.PROJECT_NAME} is running",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

