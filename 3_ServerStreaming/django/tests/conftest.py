"""Django 통합 테스트용 픽스처.

FastAPI 샘플과 동일하게, 결정론적 검증을 위해 요청 메시지를 받아 정확히
N개의 응답을 stream 으로 보내는 gRPC 서버를 백그라운드로 띄운다.
(예제의 server.py 는 time.sleep 이 있어 테스트엔 부적합하므로 직접 작성한다.)
"""

from concurrent import futures

import grpc
import pytest

from gateway import proto  # noqa: F401
import message_pb2
import message_pb2_grpc
from gateway import grpc_client

GRPC_PORT = 50053


class StreamingServicer(message_pb2_grpc.ChatServiceServicer):
    """요청 1개를 받아 N개의 ChatMessage 를 stream 으로 보낸다."""

    def __init__(self, count: int) -> None:
        self._count = count

    def ChatStream(self, request, context):
        for i in range(self._count):
            yield message_pb2.ChatMessage(message=f"{request.message} #{i}")


@pytest.fixture
def grpc_server_factory():
    servers: list[grpc.Server] = []

    def _make(count: int = 3) -> StreamingServicer:
        servicer = StreamingServicer(count)
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        message_pb2_grpc.add_ChatServiceServicer_to_server(servicer, server)
        server.add_insecure_port(f"[::]:{GRPC_PORT}")
        server.start()
        servers.append(server)
        return servicer

    # 각 테스트마다 채널을 새로 만들어 이전 서버에 대한 연결 상태가 새지 않게 한다.
    grpc_client.reset_client()
    yield _make
    grpc_client.reset_client()

    for s in servers:
        s.stop(grace=None)
