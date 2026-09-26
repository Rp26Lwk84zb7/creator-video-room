import json
import os

from creator_room.infrai_client import InfraiClient
from creator_room.room_orchestrator import AssetIntake, CreatorRoomService, RoomIntake


def main() -> None:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise SystemExit("Set INFRAI_API_KEY before running this sample")

    client = InfraiClient(api_key)
    try:
        launch = CreatorRoomService(client).launch(
            RoomIntake(
                request_id="launch-demo-001",
                room_name="friday-edit-review",
                creator_id="creator-42",
                creator_name="Mina",
                audience_id="editor-17",
                audience_name="Owen",
                region="us-east",
                asset=AssetIntake(asset_id="asset-240", title="Rough cut"),
            )
        )
        print(json.dumps(launch.model_dump(), indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
