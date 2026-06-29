"""Django 통합 테스트용 픽스처.

FastAPI 샘플과 동일하게, 결정론적 취소 검증을 위해 일정 시간 동안 작업하면서
`context.is_active()` 를 주기적으로 확인하는 gRPC 서버를 백그라운드로 띄운다.
"""

import threading
import time
from concurrent import futures

import grpc
import pytest

from gateway import proto  # noqa: F401
import cancel_example_pb2
import cancel_example_pb2_grpc
from gateway import grpc_client

GRPC_PORT = 50056

# 작업 한 번에 걸리는 총 시간(초) = STEP_COUNT * STEP_SECONDS
STEP_COUNT = 20
STEP_SECONDS = 0.05  # 총 1.0초짜리 작업


class LongRunningServicer(cancel_example_pb2_grpc.CancelServiceServicer):
    """일정 시간 동안 작업하되, 취소되면 일찍 종료하는 서비서."""

    def __init__(self) -> None:
        self.last_cancelled = threading.Event()

    def LongRunningOperation(self, request, context):
        for _ in range(STEP_COUNT):
            if not context.is_active():
                # 클라이언트가 이미 포기/취소했다 → 자원 낭비 없이 즉시 종료.
                self.last_cancelled.set()
                return cancel_example_pb2.Response(response_data="cancelled")
            time.sleep(STEP_SECONDS)  # 오래 걸리는 작업의 한 단위
        return cancel_example_pb2.Response(
            response_data=f"completed: {request.request_data}"
        )


@pytest.fixture
def grpc_server():
    servicer = LongRunningServicer()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    cancel_example_pb2_grpc.add_CancelServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()

    # 각 테스트마다 채널을 새로 만들어 이전 서버에 대한 연결 상태가 새지 않게 한다.
    grpc_client.reset_client()
    try:
        yield servicer
    finally:
        grpc_client.reset_client()
        server.stop(grace=None)
