"""통합 테스트용 픽스처.

실제 gRPC 양방향 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 그 서버를
호출하도록 한다. 결정론적 검증을 위해, 받은 각 ChatMessage 를 `echo: {message}`
로 즉시 되돌려주는 echo 서비서를 직접 작성한다(sleep/random/input 없음).
"""

from concurrent import futures

import grpc
import pytest

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import messages_pb2
import messages_pb2_grpc

GRPC_PORT = 50055
GRPC_TARGET = f"localhost:{GRPC_PORT}"


class EchoChatServicer(messages_pb2_grpc.ChatServiceServicer):
    """양방향 스트리밍 echo 서비서.

    요청 스트림의 각 메시지를 받아 즉시 `echo: {message}` 로 돌려준다.
    클라이언트가 N개를 보내면 정확히 N개를 같은 순서로 응답한다.
    """

    def Chat(self, request_iterator, context):
        for request in request_iterator:
            yield messages_pb2.ChatMessage(message=f"echo: {request.message}")


@pytest.fixture
def echo_server():
    """echo 양방향 gRPC 서버를 띄우고 테스트 종료 시 정리."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    messages_pb2_grpc.add_ChatServiceServicer_to_server(EchoChatServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    yield server
    server.stop(grace=None)
