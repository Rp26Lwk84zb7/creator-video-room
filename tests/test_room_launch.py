import json

import httpx

from creator_room.infrai_client import InfraiClient
from creator_room.room_orchestrator import AssetIntake, CreatorRoomService, RoomIntake


def test_launch_scopes_creator_and_audience_tokens() -> None:
    requests: list[httpx.Request] = []

    def responder(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content) if request.content else {}
        if request.url.path == "/v1/realtime/token/issue":
            data = {"token": f"token-for-{body['client_id']}"}
        else:
            data = {"accepted": True}
        return httpx.Response(200, json={"ok": True, "data": data, "error": None, "metadata": {}})

    client = InfraiClient("test-key", transport=httpx.MockTransport(responder))
    result = CreatorRoomService(client).launch(
        RoomIntake(
            request_id="req-8",
            room_name="cut-review",
            creator_id="creator-1",
            creator_name="Ari",
            audience_id="viewer-2",
            audience_name="Bo",
            region="eu-west",
            asset=AssetIntake(asset_id="asset-9", title="Launch cut"),
        )
    )

    token_requests = [
        json.loads(request.content)
        for request in requests
        if request.url.path == "/v1/realtime/token/issue"
    ]
    channel_requests = [
        json.loads(request.content)
        for request in requests
        if request.url.path == "/v1/realtime/channel/create"
    ]
    assert len(channel_requests) == 2
    assert all(body == {"channel": name, "type": "private"} for body, name in zip(
        channel_requests, ["cut-review", "creator-delivery:cut-review"]
    ))
    assert result.creator.can_publish is True
    assert result.audience.can_publish is False
    assert [body["capabilities"] for body in token_requests] == [
        ["publish", "subscribe"],
        ["subscribe"],
    ]
    assert all(body["channels"] == ["cut-review"] for body in token_requests)
    assert result.asset_state == "processing"
    assert all(request.headers.get("Idempotency-Key") for request in requests)

    client.close()
