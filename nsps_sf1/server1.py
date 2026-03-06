"""
Pub/Sub API: in-memory topic store, Publish and Subscribe (streaming).
Server1 - listens on 127.0.0.1:50051.
"""
import grpc
from concurrent import futures
import threading
import uuid
import time

from proto import pubsub_pb2
from proto import pubsub_pb2_grpc

TOPICS = {}
LOCK = threading.Lock()


class PubSubService(pubsub_pb2_grpc.PubSubServicer):

    def Publish(self, request, context):
        with LOCK:
            if request.topic_name not in TOPICS:
                TOPICS[request.topic_name] = []
            event = pubsub_pb2.Event(
                replay_id=str(uuid.uuid4()),
                topic_name=request.topic_name,
                payload=request.payload,
            )
            TOPICS[request.topic_name].append(event)
        print(f"Event Published -> {request.topic_name}")
        return pubsub_pb2.PublishResponse(status="SUCCESS")

    def Subscribe(self, request, context):
        topic = request.topic_name
        replay = request.replay_preset
        print("Subscriber connected")
        print(f"Topic: {topic}, Replay: {replay}")
        with LOCK:
            if topic not in TOPICS:
                TOPICS[topic] = []
        last_index = len(TOPICS[topic]) if replay == "LATEST" else 0

        while True:
            if not context.is_active():
                print("Subscriber disconnected")
                break
            with LOCK:
                events = TOPICS.get(topic, [])
                while last_index < len(events):
                    event = events[last_index]
                    last_index += 1
                    print(f"Sending Event -> {event.replay_id}")
                    yield event
            time.sleep(0.5)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pubsub_pb2_grpc.add_PubSubServicer_to_server(PubSubService(), server)
    server.add_insecure_port("127.0.0.1:50051")
    server.start()
    print("\nPub/Sub Server1 on port 50051\n")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
