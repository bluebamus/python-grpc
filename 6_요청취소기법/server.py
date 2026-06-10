import time
from concurrent import futures

import cancal_example_pb2
import cancal_example_pb2_grpc
import grpc


class CancelExampleServicer(cancal_example_pb2_grpc.CancelServiceServicer):
    def LongRunningOperation(self, request, context):
        for i in range(10):
            if context.is_active():
                print(f"Processing step {i+1}/10")
                time.sleep(1)  # Simulate work
            else:
                print("Request was cancelled by the client.")
                return cancal_example_pb2.Response(result_data="Cancelled")
        return cancal_example_pb2.Response(result_data="Completed")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    cancal_example_pb2_grpc.add_CancelServiceServicer_to_server(CancelExampleServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server started on port 50051.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
