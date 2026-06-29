"""Django 통합 테스트용 픽스처.

FastAPI 샘플과 동일하게, 받은 각 ChatMessage 를 `echo: {message}` 로 즉시
돌려주는 결정론적 echo 양방향 서비서를 직접 작성해 gRPC 서버를 띄운다.
"""

from concurrent import futures

import grpc
import pytest

from gateway import proto  # noqa: F401
import messages_pb2
import messages_pb2_grpc
from gateway import grpc_client

GRPC_PORT = 50055


class EchoChatServicer(messages_pb2_grpc.ChatServiceServicer):
    """양방향 스트리밍 echo 서비서. 받은 N개를 그대로 N개로 응답."""

    def Chat(self, request_iterator, context):
        for request in request_iterator:
            yield messages_pb2.ChatMessage(message=f"echo: {request.message}")


@pytest.fixture
def echo_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    messages_pb2_grpc.add_ChatServiceServicer_to_server(EchoChatServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()

    # 각 테스트마다 채널을 새로 만들어 이전 서버 연결 상태가 새지 않게 한다.
    grpc_client.reset_client()
    yield server
    grpc_client.reset_client()
    server.stop(grace=None)
