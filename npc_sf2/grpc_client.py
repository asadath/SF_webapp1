import grpc
import account_sync_pb2
import account_sync_pb2_grpc

SYSTEM_NAME = "NPC_SF2"
TARGET_SERVER = "localhost:50052"


def send_account(account_id, first, last, email, phone):

    channel = grpc.insecure_channel(TARGET_SERVER)

    stub = account_sync_pb2_grpc.AccountSyncServiceStub(channel)

    request = account_sync_pb2.AccountRequest(
        account_id=account_id,
        first_name=first,
        last_name=last,
        email=email,
        phone=phone,
        source_system=SYSTEM_NAME
    )

    response = stub.SyncAccount(request)

    print("Response:", response.status)