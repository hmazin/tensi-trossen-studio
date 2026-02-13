"""Config API routes."""

from fastapi import APIRouter, HTTPException

from app.config import AppConfig, load_config, save_config

router = APIRouter(tags=["config"])


@router.get("")
def get_config() -> dict:
    """Load and return current configuration."""
    config = load_config()
    return config.model_dump()


@router.post("")
def post_config(config: dict) -> dict:
    """Save configuration. Validates and persists to disk."""
    try:
        app_config = AppConfig.model_validate(config)
        save_config(app_config)
        return {"status": "saved", "config": app_config.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
