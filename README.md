# SF_webapp1

Two systems (NSPS_SF1 and NPC_SF2) with local DBs and gRPC Pub/Sub servers, and **bridges that run inside Azure Function apps** on a timer.

## Architecture

- **nsps_sf1**: Flask app (`app.py`), gRPC Server1 (`server1.py` on 50051), publisher (`publisher1.py`). **Function app** runs the bridge: subscribe to Server1 → publish to Server2 → save to NPC_SF2 DB.
- **npc_sf2**: Same pattern with Server2 (50052), publisher2. **Function app** runs the bridge: subscribe to Server2 → publish to Server1 → save to NSPS_SF1 DB.

The **bridge logic lives only in the timer-triggered function** in each project’s `function_app.py`. There is **no separate bridge process or script** to run.

## What to run

1. **Storage (local):** Start Azurite so the timer trigger can run. See `nsps_sf1/LOCAL_DEV.md` or `npc_sf2/LOCAL_DEV.md`.

2. **gRPC servers (if you need event flow):**
   - `python nsps_sf1/server1.py` (port 50051)
   - `python npc_sf2/server2.py` (port 50052)

3. **Function apps (bridges run here on a timer):**
   - `cd nsps_sf1 && func start` (or `func start --port 7072` if 7071 is in use)
   - `cd npc_sf2 && func start` (or `func start --port 7073` if 7071 is in use)

4. **Web UIs (optional):**
   - `python nsps_sf1/app.py` (e.g. port 8020)
   - `python npc_sf2/app.py` (e.g. port 8021)

## Config (function apps)

Bridge endpoints are read from environment variables (with defaults):

- **nsps_sf1** `function_app.py`: `SOURCE_GRPC_ADDRESS` (default `localhost:50051`), `DEST_GRPC_ADDRESS` (default `localhost:50052`).
- **npc_sf2** `function_app.py`: `SOURCE_GRPC_ADDRESS` (default `localhost:50052`), `DEST_GRPC_ADDRESS` (default `localhost:50051`).

To override (e.g. different hosts/ports), add them to each project’s `local.settings.json` under `Values`, or set them in your Azure Function app settings when deployed.

## Files you do **not** need to change for the bridge

- **app.py** – Web UI only; no bridge.
- **server1.py / server2.py** – gRPC servers only; no bridge.
- **publisher1.py / publisher2.py** – Used by the web app to publish events; the function app only *subscribes* and forwards.
- **db.py** – Used by both the web app and the function app (for saving bridged events); no change needed.

Only the **function app** (`function_app.py`) and the **proto** compatibility fixes (already done in both projects) are relevant for the bridge. No other files need to be updated to “adapt” to the function-app-based bridge.
