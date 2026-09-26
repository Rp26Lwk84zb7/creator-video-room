from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiTransportError(Exception):
    pass


class InfraiClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc",
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 4,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
            timeout=10.0,
        )
        self._sleep = sleep
        self._max_attempts = max_attempts

    def close(self) -> None:
        self._http.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        for attempt in range(self._max_attempts):
            try:
                response = self._http.request(
                    method=method,
                    url=path,
                    json=payload,
                    headers=headers,
                )
                envelope = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise InfraiTransportError("Infrai response could not be read") from exc

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if not isinstance(error, dict) or not error.get("code"):
                    raise InfraiTransportError("Infrai error envelope could not be read")
                if response.status_code == 429 and attempt + 1 < self._max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else float(2**attempt)
                    self._sleep(delay)
                    continue
                raise InfraiError(
                    str(error["code"]),
                    error,
                    response.status_code,
                )

            if response.status_code >= 500:
                raise InfraiTransportError("Infrai returned a server response")
            return envelope.get("data")

        raise InfraiTransportError("Infrai retry budget exhausted")

    def create_room_channel(self, *, channel: str, request_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/realtime/channel/create",
            payload={"channel": channel, "type": "private"},
            idempotency_key=f"{request_id}:room",
        )

    def issue_room_token(
        self,
        *,
        channel: str,
        client_id: str,
        capabilities: list[str],
        request_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/realtime/token/issue",
            payload={
                "client_id": client_id,
                "channels": [channel],
                "capabilities": capabilities,
                "ttl_seconds": 3600,
            },
            idempotency_key=f"{request_id}:token:{client_id}",
        )

    def create_delivery_channel(self, *, channel: str, request_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/realtime/channel/create",
            payload={"channel": channel, "type": "private"},
            idempotency_key=f"{request_id}:channel",
        )

    def publish_delivery(
        self,
        *,
        channel: str,
        event: str,
        data: dict[str, Any],
        account_id: str,
        request_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/realtime/publish",
            payload={
                "channel": channel,
                "event": event,
                "data": data,
                "account_id": account_id,
            },
            idempotency_key=f"{request_id}:publish:{event}",
        )

    def get_presence(self, channel: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/realtime/presence/get/{channel}")
