"""통합 테스트용 픽스처.

실제 gRPC 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 그 서버를
호출하도록 한다. 타임아웃(deadline) 동작을 결정론적으로 검증하기 위해,
서버가 응답 전에 일정 시간 sleep 하도록 만들 수 있는 서비서를 사용한다.
"""

import time
from concurrent import futures

import grpc
import pytest

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import wait_example_pb2
import wait_example_pb2_grpc

GRPC_PORT = 50063
GRPC_TARGET = f"localhost:{GRPC_PORT}"


class SlowEchoServicer(wait_example_pb2_grpc.EchoServiceServicer):
    """응답 전에 `sleep_s` 초 동안 일부러 지연하는 Echo 서비서.

    sleep_s 를 0 으로 주면 즉시 응답(정상 echo), 크게 주면 게이트웨이가 건
    데드라인을 초과해 DEADLINE_EXCEEDED 가 발생하도록 만들 수 있다.
    """

    def __init__(self, sleep_s: float) -> None:
        self._sleep_s = sleep_s

    def Echo(self, request, context):
        if self._sleep_s:
            time.sleep(self._sleep_s)
        return wait_example_pb2.EchoResponse(message=f"Received: {request.message}")


def _start_server(servicer) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    wait_example_pb2_grpc.add_EchoServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    return server


@pytest.fixture
def grpc_server_factory():
    """sleep_s 를 지정해 서버를 띄우는 팩토리. 테스트 종료 시 정리."""
    servers: list[grpc.Server] = []

    def _make(sleep_s: float) -> SlowEchoServicer:
        servicer = SlowEchoServicer(sleep_s)
        servers.append(_start_server(servicer))
        return servicer

    yield _make

    for s in servers:
        s.stop(grace=None)
