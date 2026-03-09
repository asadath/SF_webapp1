"""
Bridge Server2 -> Server1: subscribe to ContactChangeEvent on 50052,
skip if sourceSystem == 'Server1', forward to Server1 (50051) as AccountChangeEvent,
and save to System 1's database.
"""
import logging
import json
import grpc
import sys
import os

from proto import pubsub_pb2
from proto import pubsub_pb2_grpc

# Allow importing nsps_sf1.db from sibling folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nsps_sf1.db import (
    insert_account as insert_account_sf1,
    update_account as update_account_sf1,
    delete_account as delete_account_sf1,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def bridge_server2_to_server1():
    logger.info("Bridge Server2 -> Server1 started")
    try:
        channel_src = grpc.insecure_channel("localhost:50052")
        stub_src = pubsub_pb2_grpc.PubSubStub(channel_src)
        request_src = pubsub_pb2.SubscribeRequest(
            topic_name="ContactChangeEvent",
            replay_preset="LATEST",
        )
        events = stub_src.Subscribe(request_src)

        for event in events:
            data = json.loads(event.payload)
            header = data["ChangeEventHeader"]
            source = header.get("sourceSystem", "Server2")
            logger.info("Received from Server2 sourceSystem=%s", source)

            if source == "Server1":
                logger.info("Skip: already from Server1")
                continue

            header["sourceSystem"] = "Server2"
            channel_dest = grpc.insecure_channel("localhost:50051")
            stub_dest = pubsub_pb2_grpc.PubSubStub(channel_dest)
            resp = stub_dest.Publish(
                pubsub_pb2.PublishRequest(
                    topic_name="AccountChangeEvent",
                    payload=json.dumps(data),
                )
            )
            logger.info("Forwarded to Server1, status=%s", resp.status)
            channel_dest.close()

            # Save to System 1's database (create, update, or delete)
            full = data.get("FullData", {})
            change_type = header.get("changeType", "CREATE")
            aid = full.get("Id") or (header.get("recordIds") or [None])[0]
            first = full.get("FirstName", "")
            last = full.get("LastName", "")
            email = full.get("Email", "")
            phone = full.get("Phone", "")

            if change_type == "DELETE":
                if aid:
                    delete_account_sf1(aid)
                    logger.info("Deleted from NSPS_SF1 database: %s", aid)
            elif change_type == "UPDATE":
                update_account_sf1(aid, first, last, email, phone, source_system="NPC_SF2", created_by="grpc")
                logger.info("Updated NSPS_SF1 database for %s", aid)
            else:
                insert_account_sf1(
                    aid, first, last, email, phone,
                    "NPC_SF2",
                    created_by="grpc",
                )
                logger.info("Saved to NSPS_SF1 database")

        channel_src.close()
    except grpc.RpcError as e:
        logger.error("gRPC Error: %s", e)
    except Exception as e:
        logger.error("Error: %s", e)


if __name__ == "__main__":
    bridge_server2_to_server1()
