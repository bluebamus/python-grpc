"""통합 테스트용 픽스처.

실제 gRPC 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 그 서버를
호출하도록 한다. 서버 스트리밍을 결정론적으로 검증하기 위해, 요청 메시지를
받아 정확히 N개의 응답을 stream 으로 보내는 서비서를 사용한다.
(예제의 server.py 는 time.sleep 이 있어 테스트엔 부적합하므로 직접 작성한다.)
"""

from concurrent import futures

import grpc
import pytest

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import message_pb2
import message_pb2_grpc

GRPC_PORT = 50053
GRPC_TARGET = f"localhost:{GRPC_PORT}"


class StreamingServicer(message_pb2_grpc.ChatServiceServicer):
    """요청 1개를 받아 N개의 ChatMessage 를 stream 으로 보낸다.

    각 응답은 "{원본메시지} #{i}" 형태라, 클라이언트가 요청을 제대로 전달했는지와
    순서/개수를 모두 검증할 수 있다. sleep 없이 즉시 보내 결정론적이다.
    """

    def __init__(self, count: int) -> None:
        self._count = count

    def ChatStream(self, request, context):
        for i in range(self._count):
            yield message_pb2.ChatMessage(message=f"{request.message} #{i}")


def _start_server(servicer) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    message_pb2_grpc.add_ChatServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    return server


@pytest.fixture
def grpc_server_factory():
    """count 를 지정해 서버를 띄우는 팩토리. 테스트 종료 시 정리."""
    servers: list[grpc.Server] = []

    def _make(count: int = 3) -> StreamingServicer:
        servicer = StreamingServicer(count)
        servers.append(_start_server(servicer))
        return servicer

    yield _make

    for s in servers:
        s.stop(grace=None)
