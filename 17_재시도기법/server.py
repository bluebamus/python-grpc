import random
from concurrent import futures

import example_pb2
import example_pb2_grpc
import grpc


class ExampleServiceServicer(example_pb2_grpc.ExampleServiceServicer):
    def UnaryCall(self, request, context):
        # 의도적으로 50% 확률로 실패하도록 구현 (재시도 정책 동작 확인용)
        if random.random() < 0.5:
            print("Request failed intentionally (UNAVAILABLE).")
            context.abort(grpc.StatusCode.UNAVAILABLE, "Service is temporarily unavailable.")
        print("Request succeeded.")
        return example_pb2.ExampleResponse(message=f"Received: {request.message}")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    example_pb2_grpc.add_ExampleServiceServicer_to_server(ExampleServiceServicer(), server)
    server.add_insecure_port('[::]:50051')

    server.start()
    print("Server started on port 50051.")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
