"""
Bridge Server1 -> Server2: subscribe to AccountChangeEvent on 50051,
skip if sourceSystem == 'Server2', forward to Server2 (50052) as ContactChangeEvent,
and save to System 2's database.
"""
import logging
import json
import grpc
import sys
import os

from proto import pubsub_pb2
from proto import pubsub_pb2_grpc

# Allow importing npc_sf2.db from sibling folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from npc_sf2.db import insert_account as insert_account_sf2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def bridge_server1_to_server2():
    logger.info("Bridge Server1 -> Server2 started")
    try:
        channel_src = grpc.insecure_channel("localhost:50051")
        stub_src = pubsub_pb2_grpc.PubSubStub(channel_src)
        request_src = pubsub_pb2.SubscribeRequest(
            topic_name="AccountChangeEvent",
            replay_preset="LATEST",
        )
        events = stub_src.Subscribe(request_src)

        for event in events:
            data = json.loads(event.payload)
            header = data["ChangeEventHeader"]
            source = header.get("sourceSystem", "Server1")
            logger.info("Received from Server1 sourceSystem=%s", source)

            if source == "Server2":
                logger.info("Skip: already from Server2")
                continue

            header["sourceSystem"] = "Server1"
            channel_dest = grpc.insecure_channel("localhost:50052")
            stub_dest = pubsub_pb2_grpc.PubSubStub(channel_dest)
            resp = stub_dest.Publish(
                pubsub_pb2.PublishRequest(
                    topic_name="ContactChangeEvent",
                    payload=json.dumps(data),
                )
            )
            logger.info("Forwarded to Server2, status=%s", resp.status)
            channel_dest.close()

            # Save to System 2's database so it appears in NPC_SF2's account list (created via gRPC event)
            full = data.get("FullData", {})
            insert_account_sf2(
                full.get("Id", ""),
                full.get("FirstName", ""),
                full.get("LastName", ""),
                full.get("Email", ""),
                full.get("Phone", ""),
                "NSPS_SF1",
                created_by="grpc",
            )
            logger.info("Saved to NPC_SF2 database")

        channel_src.close()
    except grpc.RpcError as e:
        logger.error("gRPC Error: %s", e)
    except Exception as e:
        logger.error("Error: %s", e)


if __name__ == "__main__":
    bridge_server1_to_server2()
