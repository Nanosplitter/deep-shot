"""NFL stats API routes."""

from fastapi import APIRouter, Depends, HTTPException
import logging

from app.config.settings import Settings, get_settings
from app.models.schemas import NFLInput, NFLResponse
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


@router.post("/process", response_model=NFLResponse)
async def process_input(
    request: NFLInput,
    service: NFLService = Depends(get_nfl_service),
) -> NFLResponse:
    """Process an NFL stats query and return a response."""
    logger.info(f"Processing input: {request.input[:100]}...")
    try:
        response = await service.process(request.input)
        logger.info(f"Response generated after {response.attempts} attempt(s)")
        return response
    except Exception as e:
        logger.exception("Error processing request")
        raise HTTPException(status_code=500, detail=str(e))
