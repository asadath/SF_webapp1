"""
Publishes Account CDC events to Server1 (localhost:50051).
Exposes send_account() for the web app to publish on create.
"""
import grpc
import json
from datetime import datetime, UTC

from proto import pubsub_pb2
from proto import pubsub_pb2_grpc

SYSTEM_NAME = "Server1"
TARGET = "localhost:50051"
TOPIC = "AccountChangeEvent"


def _publish(payload_dict):
    payload = json.dumps(payload_dict)
    channel = grpc.insecure_channel(TARGET)
    stub = pubsub_pb2_grpc.PubSubStub(channel)
    resp = stub.Publish(
        pubsub_pb2.PublishRequest(topic_name=TOPIC, payload=payload)
    )
    channel.close()
    return resp


def send_account(account_id, first, last, email, phone):
    """Publish one Account CDC event to Server1 (used by app.py on create)."""
    payload = {
        "eventId": f"evt_{account_id[:8]}",
        "ChangeEventHeader": {
            "entityName": "Account",
            "changeType": "CREATE",
            "recordIds": [account_id],
            "commitTimestamp": datetime.now(UTC).isoformat(),
            "changedFields": ["Name"],
            "sourceSystem": SYSTEM_NAME,
        },
        "FullData": {
            "Id": account_id,
            "Name": f"{first} {last}".strip() or "N/A",
            "FirstName": first,
            "LastName": last,
            "Email": email,
            "Phone": phone,
            "LastModifiedDate": datetime.now(UTC).isoformat(),
        },
    }
    resp = _publish(payload)
    print("Publish response:", resp.status)
