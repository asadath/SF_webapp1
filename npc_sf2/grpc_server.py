import grpc
from concurrent import futures

import account_sync_pb2
import account_sync_pb2_grpc

from db import insert_account

SYSTEM_NAME = "NPC_SF2"


class AccountSyncService(
    account_sync_pb2_grpc.AccountSyncServiceServicer
):

    def SyncAccount(self, request, context):

        print("Received Account:")
        print(request)

        # Loop prevention
        if request.source_system == SYSTEM_NAME:
            print("Ignored own message")
            return account_sync_pb2.SyncResponse(status="Ignored")

        insert_account(
            request.account_id,
            request.first_name,
            request.last_name,
            request.email,
            request.phone,
            request.source_system
        )

        print("Saved account from remote system")

        return account_sync_pb2.SyncResponse(status="Success")


def serve():

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )

    account_sync_pb2_grpc.add_AccountSyncServiceServicer_to_server(
        AccountSyncService(),
        server
    )

    server.add_insecure_port("[::]:50052")

    server.start()

    print("NSPS_SF1 gRPC Server running on port 50052")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()