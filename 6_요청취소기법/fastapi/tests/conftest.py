"""통합 테스트용 픽스처.

실제 gRPC 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 그 서버를
호출하도록 한다. 요청 취소를 결정론적으로 검증하기 위해, 일정 시간 동안
작업하면서 `context.is_active()` 를 주기적으로 확인하는 서비서를 사용한다.

- 데드라인이 충분하면 작업을 끝까지 수행하고 결과를 돌려준다.
- 데드라인이 짧으면 클라이언트가 먼저 포기하고, 서버 context 가 비활성화되어
  서버도 일찍 종료한다(취소 가능 작업 시연).
"""

import threading
import time
from concurrent import futures

import grpc
import pytest

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import cancel_example_pb2
import cancel_example_pb2_grpc

GRPC_PORT = 50056
GRPC_TARGET = f"localhost:{GRPC_PORT}"

# 작업 한 번에 걸리는 총 시간(초) = STEP_COUNT * STEP_SECONDS
STEP_COUNT = 20
STEP_SECONDS = 0.05  # 총 1.0초짜리 작업


class LongRunningServicer(cancel_example_pb2_grpc.CancelServiceServicer):
    """일정 시간 동안 작업하되, 취소되면 일찍 종료하는 서비서.

    실제 server.py 처럼 time.sleep 으로 오래 걸리는 작업을 흉내내되, 매 스텝마다
    `context.is_active()` 를 확인한다. 클라이언트가 데드라인을 넘기거나 호출을
    취소하면 context 가 비활성화되므로, 남은 작업을 건너뛰고 즉시 반환한다.
    """

    def __init__(self) -> None:
        # 마지막 호출이 취소로 끝났는지 테스트가 확인할 수 있게 기록한다.
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


def _start_server(servicer) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    cancel_example_pb2_grpc.add_CancelServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    return server


@pytest.fixture
def grpc_server():
    """취소 가능 서비서를 띄우고, 테스트 종료 시 정리한다."""
    servicer = LongRunningServicer()
    server = _start_server(servicer)
    try:
        yield servicer
    finally:
        server.stop(grace=None)
