"""TENSI Trossen Studio - FastAPI backend."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import load_config
from app.routes import config_routes, process_routes, camera_routes
from app.services.camera_manager import CameraManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    # Startup
    yield
    # Shutdown - only shutdown local cameras if managed by this instance
    config = load_config()
    if config.robot.enable_local_cameras:
        CameraManager.get_instance().shutdown_all()


app = FastAPI(
    title="TENSI Trossen Studio",
    description="Web GUI for LeRobot Trossen - teleoperation, recording, training, replay",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:5174", 
        "http://127.0.0.1:5173", 
        "http://127.0.0.1:5174",
        # Allow any IP on local network for distributed setup
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_routes.router, prefix="/api/config")
app.include_router(process_routes.router)
app.include_router(camera_routes.router)


@app.get("/")
def root() -> dict:
    """Root redirect with API info."""
    return {
        "service": "TENSI Trossen Studio",
        "docs": "/docs",
        "health": "/health",
        "frontend": "http://localhost:5173",
    }


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "tensi-trossen-studio"}


def run() -> None:
    """Run the server (for `studio` CLI)."""
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
