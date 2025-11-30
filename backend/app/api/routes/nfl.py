"""NFL stats API routes."""

from fastapi import APIRouter, Depends, HTTPException
import logging

from app.config.settings import Settings, get_settings
from app.models.schemas import NFLChatInput, NFLResponse
from app.services.nfl_service import NFLService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/nfl", tags=["nfl"])

_service_cache: dict[int, NFLService] = {}


def get_nfl_service(settings: Settings = Depends(get_settings)) -> NFLService:
    """Dependency to get or create NFLService instance."""
    settings_id = id(settings)
    if settings_id not in _service_cache:
        _service_cache[settings_id] = NFLService(settings)
    return _service_cache[settings_id]


@router.post("/chat", response_model=NFLResponse)
async def process_chat(
    request: NFLChatInput,
    service: NFLService = Depends(get_nfl_service),
) -> NFLResponse:
    """Process a multi-turn NFL stats conversation and return a response."""
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    latest_content = request.messages[-1].content if request.messages else ""
    logger.info(
        f"Processing chat with {len(request.messages)} message(s): {latest_content[:100]}..."
    )
    try:
        response = await service.process_chat(request.messages)
        logger.info(f"Response generated after {response.attempts} attempt(s)")
        return response
    except Exception as e:
        logger.exception("Error processing chat request")
        raise HTTPException(status_code=500, detail=str(e))
