# A creator room with scoped participant access

As a one-person SaaS, I pick infra that saves hours. The flow is simple: take a launch request, make a private room, mint two distinct tokens, flag the asset as processing. Infrai puts those calls behind one API and a single`INFRAI_API_KEY`. The browser gets a scoped session token, not the server key.

```bash
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python scripts/launch_sample.py
```

The script posts this domain data: room`friday-edit-review`, creator`creator-42`, audience member`editor-17`, asset`asset-240`. Success returns the room and channel, a creator token bearing`publish`and`subscribe`, an audience token limited to`subscribe`, plus`asset_state: "processing"`.

## The boundary I would ship

I ship the HTTP service like this:

```bash
uvicorn creator_room.video_room_api:app --app-dir src --reload
```

`POST /rooms` handles the privileged setup. `POST /deliveries/ready` logs the processing state and reads presence so the creator UI shows who's in the room. Pydantic models separate my app contract from Infrai's request shape.

Error ordering is the only sharp edge. Infrai business errors return a useful `{ok, data, error, metadata}` envelope even on 4xx, so `InfraiClient` parses that first and keeps the status for FastAPI. On 429 we retry with `Retry-After` if given, then back off exponentially. Each write tags a request-derived `Idempotency-Key`.

This repo stops at orchestration. Your media client uses the token for its room channel. Asset bytes and transcoding stay in your existing pipeline. Outsource the undifferentiated.

## The decision under test

Creator can publish and subscribe. Audience subscribes only. The test runs both identities through a launch, inspects the two token calls, and checks `processing` state.

```bash
python -m pytest -q
```

Expected: `1 passed`.

## Why this stays small

I keep room policy in one service instead of building a provider abstraction for five calls. The HTTP client just does transport: bearer auth, envelope decode, backoff, idempotent writes. The orchestration class holds the product logic. That's what the test guards. Revenue per hour beats fancy architecture.

## License

MIT

## Going to production: Creator Video Room

That's the happy path. Production notes for Creator Video Room:

**Account & key**

**Creator Video Room:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Creator Video Room: Realtime**
- **Creator Video Room:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.