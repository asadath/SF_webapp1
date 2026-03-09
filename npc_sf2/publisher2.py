"""
Publishes Contact CDC events to Server2 (localhost:50052).
Exposes send_account() for the web app to publish on create.
"""
import grpc
import json
from datetime import datetime, UTC

from proto import pubsub_pb2
from proto import pubsub_pb2_grpc

SYSTEM_NAME = "Server2"
TARGET = "localhost:50052"
TOPIC = "ContactChangeEvent"


def _publish(payload_dict):
    payload = json.dumps(payload_dict)
    channel = grpc.insecure_channel(TARGET)
    stub = pubsub_pb2_grpc.PubSubStub(channel)
    resp = stub.Publish(
        pubsub_pb2.PublishRequest(topic_name=TOPIC, payload=payload)
    )
    channel.close()
    return resp


def _payload(account_id, first, last, email, phone, change_type):
    return {
        "eventId": f"evt_contact_{account_id[:8]}",
        "ChangeEventHeader": {
            "entityName": "Contact",
            "changeType": change_type,
            "recordIds": [account_id],
            "commitTimestamp": datetime.now(UTC).isoformat(),
            "changedFields": ["FirstName", "LastName", "Email", "Phone"],
            "sourceSystem": SYSTEM_NAME,
        },
        "FullData": {
            "Id": account_id,
            "FirstName": first,
            "LastName": last,
            "Email": email,
            "Phone": phone,
            "LastModifiedDate": datetime.now(UTC).isoformat(),
        },
    }


def send_account(account_id, first, last, email, phone):
    """Publish one Contact CDC event to Server2 (used by app.py on create)."""
    payload = _payload(account_id, first, last, email, phone, "CREATE")
    resp = _publish(payload)
    print("Publish response:", resp.status)


def send_account_update(account_id, first, last, email, phone):
    """Publish Contact UPDATE event to Server2 (used by app.py on edit save)."""
    payload = _payload(account_id, first, last, email, phone, "UPDATE")
    resp = _publish(payload)
    print("Publish update response:", resp.status)


def send_account_delete(account_id):
    """Publish Contact DELETE event to Server2 (used by app.py on delete)."""
    payload = {
        "eventId": f"evt_del_contact_{account_id[:8]}",
        "ChangeEventHeader": {
            "entityName": "Contact",
            "changeType": "DELETE",
            "recordIds": [account_id],
            "commitTimestamp": datetime.now(UTC).isoformat(),
            "sourceSystem": SYSTEM_NAME,
        },
        "FullData": {},
    }
    resp = _publish(payload)
    print("Publish delete response:", resp.status)
