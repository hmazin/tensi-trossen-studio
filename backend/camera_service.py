"""Standalone Camera Service - FastAPI backend for distributed camera management.

This service runs independently on the follower PC to manage RealSense cameras.
It provides camera streaming and shutdown endpoints for remote access.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import camera_routes
from app.services.camera_manager import CameraManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    # Startup
    yield
    # Shutdown
    CameraManager.get_instance().shutdown_all()


app = FastAPI(
    title="TENSI Trossen Camera Service",
    description="Distributed camera management for LeRobot Trossen - camera streaming and control",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration - allow requests from any origin on local network
# In production, restrict to specific IPs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for flexibility in distributed setup
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register only camera routes
app.include_router(camera_routes.router)


@app.get("/")
def root() -> dict:
    """Root redirect with API info."""
    return {
        "service": "TENSI Trossen Camera Service",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "tensi-camera-service"}


def run() -> None:
    """Run the camera service (for CLI)."""
    import uvicorn

    uvicorn.run("camera_service:app", host="0.0.0.0", port=8001, reload=True)
