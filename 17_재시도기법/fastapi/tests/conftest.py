"""통합 테스트용 픽스처.

실제 gRPC 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 그 서버를
호출하도록 한다. 재시도 동작을 결정론적으로 검증하기 위해, 처음 N번은
UNAVAILABLE 로 실패하고 그 이후 성공하는 서비서를 사용한다.
"""

import threading
from concurrent import futures

import grpc
import pytest

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import example_pb2
import example_pb2_grpc

GRPC_PORT = 50051
GRPC_TARGET = f"localhost:{GRPC_PORT}"


class FlakyServicer(example_pb2_grpc.ExampleServiceServicer):
    """처음 `fail_times` 번은 UNAVAILABLE, 이후 성공.

    fail_times 를 매우 크게 주면 '영구 실패'를 흉내낼 수 있다.
    """

    def __init__(self, fail_times: int) -> None:
        self._fail_times = fail_times
        self._calls = 0
        self._lock = threading.Lock()

    @property
    def calls(self) -> int:
        return self._calls

    def UnaryCall(self, request, context):
        with self._lock:
            self._calls += 1
            should_fail = self._calls <= self._fail_times
        if should_fail:
            context.abort(grpc.StatusCode.UNAVAILABLE, "temporarily unavailable")
        return example_pb2.ExampleResponse(message=f"Received: {request.message}")


def _start_server(servicer) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    example_pb2_grpc.add_ExampleServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    return server


@pytest.fixture
def grpc_server_factory():
    """fail_times 를 지정해 서버를 띄우는 팩토리. 테스트 종료 시 정리."""
    servers: list[grpc.Server] = []

    def _make(fail_times: int) -> FlakyServicer:
        servicer = FlakyServicer(fail_times)
        servers.append(_start_server(servicer))
        return servicer

    yield _make

    for s in servers:
        s.stop(grace=None)
