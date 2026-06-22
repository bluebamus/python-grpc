import time
from concurrent import futures

import grpc
import wait_example_pb2
import wait_example_pb2_grpc


class EchoServiceServicer(wait_example_pb2_grpc.EchoServiceServicer):
    def Echo(self, request, context):
        # Simulate a long-running operation
        time.sleep(2)
        return wait_example_pb2.EchoResponse(message=request.message)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    wait_example_pb2_grpc.add_EchoServiceServicer_to_server(EchoServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server started on port 50051")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()