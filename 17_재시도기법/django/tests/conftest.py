"""Django 통합 테스트용 픽스처.

FastAPI 샘플과 동일하게, 결정론적 재시도 검증을 위해 처음 N번 실패 후
성공하는 gRPC 서버를 백그라운드로 띄운다.
"""

import threading
from concurrent import futures

import grpc
import pytest

from gateway import proto  # noqa: F401
import example_pb2
import example_pb2_grpc
from gateway import grpc_client

GRPC_PORT = 50051


class FlakyServicer(example_pb2_grpc.ExampleServiceServicer):
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


@pytest.fixture
def grpc_server_factory():
    servers: list[grpc.Server] = []

    def _make(fail_times: int) -> FlakyServicer:
        servicer = FlakyServicer(fail_times)
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        example_pb2_grpc.add_ExampleServiceServicer_to_server(servicer, server)
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
