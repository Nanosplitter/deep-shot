"""NFL stats API routes."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import logging
import json

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


@router.post("/chat/stream")
async def process_chat_stream(
    request: NFLChatInput,
    service: NFLService = Depends(get_nfl_service),
) -> StreamingResponse:
    """Process a multi-turn NFL stats conversation with streaming progress updates."""
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    latest_content = request.messages[-1].content if request.messages else ""
    logger.info(
        f"Processing streaming chat with {len(request.messages)} message(s): {latest_content[:100]}..."
    )

    async def event_generator():
        try:
            async for event in service.process_chat_streaming(request.messages):
                yield f"data: {event.model_dump_json()}\n\n"
        except Exception as e:
            logger.exception("Error in streaming chat")
            error_event = {
                "event": "error",
                "step": "error",
                "message": str(e),
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
