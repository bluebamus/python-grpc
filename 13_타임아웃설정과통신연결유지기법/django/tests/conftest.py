"""Django 통합 테스트용 픽스처.

FastAPI 샘플과 동일하게, 결정론적 deadline 검증을 위해 응답 전에 일정 시간
sleep 할 수 있는 gRPC 서버를 백그라운드로 띄운다.
"""

import time
from concurrent import futures

import grpc
import pytest

from gateway import proto  # noqa: F401
import wait_example_pb2
import wait_example_pb2_grpc
from gateway import grpc_client

GRPC_PORT = 50063


class SlowEchoServicer(wait_example_pb2_grpc.EchoServiceServicer):
    """응답 전에 `sleep_s` 초 지연하는 Echo 서비서."""

    def __init__(self, sleep_s: float) -> None:
        self._sleep_s = sleep_s

    def Echo(self, request, context):
        if self._sleep_s:
            time.sleep(self._sleep_s)
        return wait_example_pb2.EchoResponse(message=f"Received: {request.message}")


@pytest.fixture
def grpc_server_factory():
    servers: list[grpc.Server] = []

    def _make(sleep_s: float) -> SlowEchoServicer:
        servicer = SlowEchoServicer(sleep_s)
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        wait_example_pb2_grpc.add_EchoServiceServicer_to_server(servicer, server)
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
