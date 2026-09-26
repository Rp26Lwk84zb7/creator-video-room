from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .infrai_client import InfraiClient


class AssetIntake(BaseModel):
    asset_id: str = Field(min_length=1)
    title: str = Field(min_length=1)


class RoomIntake(BaseModel):
    request_id: str = Field(min_length=1)
    room_name: str = Field(min_length=1)
    creator_id: str = Field(min_length=1)
    creator_name: str = Field(min_length=1)
    audience_id: str = Field(min_length=1)
    audience_name: str = Field(min_length=1)
    region: str = Field(min_length=1)
    max_participants: int = Field(default=25, ge=2, le=500)
    asset: AssetIntake


class ParticipantAccess(BaseModel):
    identity: str
    token: str
    can_publish: bool
    can_subscribe: bool


class RoomLaunch(BaseModel):
    room: str
    delivery_channel: str
    creator: ParticipantAccess
    audience: ParticipantAccess
    asset_state: str


class DeliveryUpdate(BaseModel):
    request_id: str = Field(min_length=1)
    room: str = Field(min_length=1)
    creator_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    rendition_id: str = Field(min_length=1)


class CreatorRoomService:
    def __init__(self, infrai: InfraiClient) -> None:
        self._infrai = infrai

    def launch(self, intake: RoomIntake) -> RoomLaunch:
        self._infrai.create_room_channel(
            channel=intake.room_name,
            request_id=intake.request_id,
        )
        room = intake.room_name
        channel = f"creator-delivery:{room}"
        self._infrai.create_delivery_channel(channel=channel, request_id=intake.request_id)

        creator_token = self._infrai.issue_room_token(
            channel=room,
            client_id=intake.creator_id,
            capabilities=["publish", "subscribe"],
            request_id=intake.request_id,
        )
        audience_token = self._infrai.issue_room_token(
            channel=room,
            client_id=intake.audience_id,
            capabilities=["subscribe"],
            request_id=intake.request_id,
        )
        self._infrai.publish_delivery(
            channel=channel,
            event="asset.processing",
            data={"asset_id": intake.asset.asset_id, "title": intake.asset.title},
            account_id=intake.creator_id,
            request_id=intake.request_id,
        )
        return RoomLaunch(
            room=room,
            delivery_channel=channel,
            creator=self._access(intake.creator_id, creator_token, can_publish=True),
            audience=self._access(intake.audience_id, audience_token, can_publish=False),
            asset_state="processing",
        )

    def mark_ready(self, update: DeliveryUpdate) -> dict[str, Any]:
        channel = f"creator-delivery:{update.room}"
        published = self._infrai.publish_delivery(
            channel=channel,
            event="asset.ready",
            data={"asset_id": update.asset_id, "rendition_id": update.rendition_id},
            account_id=update.creator_id,
            request_id=update.request_id,
        )
        presence = self._infrai.get_presence(channel)
        return {"state": "ready", "published": published, "presence": presence}

    @staticmethod
    def _access(identity: str, token_data: dict[str, Any], *, can_publish: bool) -> ParticipantAccess:
        return ParticipantAccess(
            identity=identity,
            token=str(token_data["token"]),
            can_publish=can_publish,
            can_subscribe=True,
        )
