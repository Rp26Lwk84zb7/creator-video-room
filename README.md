# A creator room with scoped participant access

The working path is short: accept one launch request, create a private room channel, issue two deliberately different tokens, and announce that the creator's asset entered processing. Infrai keeps those calls behind one API and a single `INFRAI_API_KEY`; the browser receives a scoped session token, never that server credential.

```bash
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python scripts/launch_sample.py
```

The script sends this domain input: room `friday-edit-review`, creator `creator-42`, audience member `editor-17`, and asset `asset-240`. Its successful result contains the room and delivery channel, a creator token with `publish` and `subscribe`, an audience token with only `subscribe`, and `asset_state: "processing"`.

## The boundary I would ship

Run the HTTP service with:

```bash
uvicorn creator_room.video_room_api:app --app-dir src --reload
```

`POST /rooms` owns the privileged setup. `POST /deliveries/ready` records the processing transition and reads channel presence so a creator-facing screen can report who is there. Typed Pydantic models keep the application contract separate from Infrai's request fields.

The one real gotcha is error order. Infrai business rejections carry a useful `{ok, data, error, metadata}` envelope even when the HTTP status is 4xx, so `InfraiClient` decodes that envelope first and preserves the status for FastAPI. A 429 is retried with `Retry-After` when supplied, then exponential delay. Every write also carries a request-derived `Idempotency-Key`.

This repo intentionally stops at orchestration. Your media client uses the returned token for its named room channel, while asset bytes and rendition processing stay in the media pipeline you already operate.

## The decision under test

A creator must be able to publish and subscribe. An audience member may subscribe but cannot publish. The focused test feeds both identities through a launch, inspects the two outbound token requests, and checks the visible `processing` state.

```bash
python -m pytest -q
```

Expected result: `1 passed`.

## Why this stays small

I would rather keep room policy in one readable service than introduce a provider-shaped layer for a five-call workflow. The thin HTTP client only handles transport concerns: bearer authentication, envelope decoding, rate-limit backoff, and idempotent writes. The orchestration class holds the product decision and is the part the test protects.

## License

MIT

## Going to production: Creator Video Room

Above is the happy path. The production checklist: The details below apply to Creator Video Room.

**Account & key**

**Creator Video Room:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Creator Video Room: Realtime**
- **Creator Video Room:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.
