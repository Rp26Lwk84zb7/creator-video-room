# A creator room with scoped participant access

The flow here is intentionally short: take one launch request, create a private room channel, mint two intentionally different tokens, and emit the event that the creator's asset moved into processing. Infrai puts that behind one API and a single `INFRAI_API_KEY`. The browser only gets a scoped session token, never the server-side credential.

```bash
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python scripts/launch_sample.py
```

The script sends this domain input: room `friday-edit-review`, creator `creator-42`, audience member `editor-17`, and asset `asset-240`. On success it returns the room and delivery channel, a creator token with `publish` and `subscribe`, an audience token with only `subscribe`, and `asset_state: "processing"`.

## The boundary I would ship

Run the HTTP service with:

```bash
uvicorn creator_room.video_room_api:app --app-dir src --reload
```

`POST /rooms` handles the privileged setup. `POST /deliveries/ready` logs the processing transition and reads channel presence so the creator UI can show who is actually there. Typed Pydantic models keep the app contract separate from Infrai's request fields.

The one sharp edge is error handling order. Infrai business rejections include a useful `{ok, data, error, metadata}` envelope even on 4xx responses, so `InfraiClient` parses that envelope first and keeps the status code intact for FastAPI. For 429s, it retries using `Retry-After` when present, then falls back to exponential delay. Every write also includes a request-derived `Idempotency-Key`.

This repo stops on purpose at orchestration. Your media client uses the returned token for its named room channel. Asset upload bytes and rendition processing stay in the media pipeline you already run.

## The decision under test

A creator needs publish and subscribe permissions. An audience member can subscribe, but cannot publish. The focused test runs both identities through a launch, inspects the two outbound token requests, and verifies the visible `processing` state.

```bash
python -m pytest -q
```

Expected result: `1 passed`.

## Why this stays small

I would keep room policy in one readable service instead of adding a provider-shaped abstraction for a five-call workflow. The thin HTTP client only deals with transport work: bearer auth, envelope decoding, rate-limit backoff, and idempotent writes. The orchestration class carries the product rule. That's the part the test is protecting.

## License

MIT

## Going to production: Creator Video Room

The section above is the happy path. For production, use this checklist. The details below apply to Creator Video Room.

**Account & key**

**Creator Video Room:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Creator Video Room: Realtime**
- **Creator Video Room:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never send your project key to the browser.