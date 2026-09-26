from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .infrai_client import InfraiClient, InfraiError, InfraiTransportError
from .room_orchestrator import CreatorRoomService, DeliveryUpdate, RoomIntake, RoomLaunch


def build_service() -> CreatorRoomService:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set INFRAI_API_KEY before starting the service")
    return CreatorRoomService(InfraiClient(api_key))


app = FastAPI(title="Creator video room")


@app.exception_handler(InfraiError)
async def handle_infrai_error(_request: object, exc: InfraiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(InfraiTransportError)
async def handle_transport_error(_request: object, exc: InfraiTransportError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.post("/rooms", response_model=RoomLaunch, status_code=201)
def create_room(intake: RoomIntake) -> RoomLaunch:
    return build_service().launch(intake)


@app.post("/deliveries/ready")
def complete_delivery(update: DeliveryUpdate) -> dict[str, object]:
    return build_service().mark_ready(update)
