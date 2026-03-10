import datetime
import json
import logging
import grpc
import os
import sys
import time

import azure.functions as func

# -----------------------------------------------------------------------------
# Path setup
# -----------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Import generated gRPC files
from proto import pubsub_pb2
from proto import pubsub_pb2_grpc

# Import sibling project DB helpers
from npc_sf2.db import (
    insert_account as insert_account_sf2,
    update_account as update_account_sf2,
    delete_account as delete_account_sf2,
)

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Azure Function App
# -----------------------------------------------------------------------------
app = func.FunctionApp()

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
SOURCE_GRPC_ADDRESS = os.getenv("SOURCE_GRPC_ADDRESS", "localhost:50051")
DEST_GRPC_ADDRESS = os.getenv("DEST_GRPC_ADDRESS", "localhost:50052")

SOURCE_TOPIC = os.getenv("SOURCE_TOPIC", "AccountChangeEvent")
DEST_TOPIC = os.getenv("DEST_TOPIC", "ContactChangeEvent")

# Max run time per timer invocation (safety cap to stay under function timeout).
# After this, we exit so the next timer tick can reconnect. Default 4 min.
MAX_RUN_SECONDS = int(os.getenv("MAX_RUN_SECONDS", "240"))

# gRPC: long timeout on Subscribe so the stream stays open until error/end (not idle timeout).
SUBSCRIBE_RPC_TIMEOUT = int(os.getenv("SUBSCRIBE_RPC_TIMEOUT", "3600"))
PUBLISH_RPC_TIMEOUT = int(os.getenv("PUBLISH_RPC_TIMEOUT", "10"))


def save_to_npc_sf2(data: dict, source_system: str) -> None:
    """
    Save event payload into NPC_SF2 database based on change type.
    """
    header = data.get("ChangeEventHeader", {})
    full = data.get("FullData", {})

    change_type = (header.get("changeType") or "CREATE").upper()
    record_ids = header.get("recordIds") or []

    account_id = full.get("Id") or (record_ids[0] if record_ids else None)
    first = full.get("FirstName", "")
    last = full.get("LastName", "")
    email = full.get("Email", "")
    phone = full.get("Phone", "")

    if not account_id:
        logger.warning("Skipping DB save because account/contact id is missing")
        return

    if change_type == "DELETE":
        delete_account_sf2(account_id)
        logger.info("Deleted from NPC_SF2 database: %s", account_id)

    elif change_type == "UPDATE":
        update_account_sf2(
            account_id,
            first,
            last,
            email,
            phone,
            source_system=source_system,
            created_by="grpc",
        )
        logger.info("Updated NPC_SF2 database for %s", account_id)

    else:
        insert_account_sf2(
            account_id,
            first,
            last,
            email,
            phone,
            source_system,
            created_by="grpc",
        )
        logger.info("Inserted into NPC_SF2 database: %s", account_id)


def process_single_event(event) -> None:
    """
    Process one event from Server1, forward to Server2, then save to NPC_SF2 DB.
    """
    data = json.loads(event.payload)
    header = data.get("ChangeEventHeader", {})

    source = header.get("sourceSystem", "Server1")
    logger.info("Received event from sourceSystem=%s", source)

    if source == "Server2":
        logger.info("Skipping event because it already originated from Server2")
        return

    # Preserve origin as Server1 before forwarding
    header["sourceSystem"] = "Server1"

    with grpc.insecure_channel(DEST_GRPC_ADDRESS) as channel_dest:
        stub_dest = pubsub_pb2_grpc.PubSubStub(channel_dest)
        resp = stub_dest.Publish(
            pubsub_pb2.PublishRequest(
                topic_name=DEST_TOPIC,
                payload=json.dumps(data),
            ),
            timeout=PUBLISH_RPC_TIMEOUT,
        )
        logger.info("Forwarded to Server2, publish status=%s", resp.status)

    save_to_npc_sf2(data, source_system="NSPS_SF1")


def bridge_server1_to_server2_once(max_run_seconds: int) -> int:
    """
    Timer only initiates the gRPC subscription. Once the channel is established,
    we stay in the Subscribe loop until the stream ends, errors, or we hit
    max_run_seconds (safety cap). Next timer tick will reconnect if we exited.
    """
    processed = 0
    start = time.time()

    logger.info(
        "Bridge Server1 -> Server2: connecting. Source=%s Dest=%s (will run until stream end/error or %ss cap)",
        SOURCE_GRPC_ADDRESS,
        DEST_GRPC_ADDRESS,
        max_run_seconds,
    )

    try:
        with grpc.insecure_channel(SOURCE_GRPC_ADDRESS) as channel_src:
            stub_src = pubsub_pb2_grpc.PubSubStub(channel_src)

            request_src = pubsub_pb2.SubscribeRequest(
                topic_name=SOURCE_TOPIC,
                replay_preset="LATEST",
            )

            events = stub_src.Subscribe(
                request_src,
                timeout=SUBSCRIBE_RPC_TIMEOUT,
            )

            for event in events:
                if (time.time() - start) >= max_run_seconds:
                    logger.info("Run time cap reached; exiting so next timer tick can reconnect")
                    break

                try:
                    process_single_event(event)
                    processed += 1
                except Exception as event_ex:
                    logger.exception("Failed processing one event: %s", event_ex)

    except grpc.RpcError as grpc_ex:
        logger.error("gRPC error during bridge execution (next timer tick will reconnect): %s", grpc_ex)
    except Exception as ex:
        logger.exception("Unexpected bridge error (next timer tick will reconnect): %s", ex)

    logger.info("Bridge run finished. Total processed=%s", processed)
    return processed


@app.timer_trigger(
    schedule="*/1 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def timer_trigger(myTimer: func.TimerRequest) -> None:
    """
    Timer only starts the gRPC subscription. Once connected, the channel stays
    open and processes events until the stream ends, errors, or run-time cap.
    Next timer tick reconnects if the previous run exited.
    """
    utc_now = datetime.datetime.utcnow().isoformat()

    if myTimer.past_due:
        logger.warning("The timer is past due!")

    logger.info("Timer trigger started at %s (initiating gRPC subscription)", utc_now)

    processed = bridge_server1_to_server2_once(MAX_RUN_SECONDS)

    logger.info("Timer run completed. Events processed=%s", processed)