"""통합 테스트용 픽스처.

실제 gRPC 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 그 서버를
호출하도록 한다. 예제의 server.py 는 학습용이라 그대로 쓰지 않고,
결정론적으로 동작하는 test 서비서를 직접 작성한다.
"""

from concurrent import futures

import grpc
import pytest

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import helloworld_pb2
import helloworld_pb2_grpc

GRPC_PORT = 50052
GRPC_TARGET = f"localhost:{GRPC_PORT}"

# 백엔드 INVALID_ARGUMENT 매핑을 검증하기 위한 sentinel.
# 이 이름으로 호출하면 백엔드가 INVALID_ARGUMENT 로 abort 한다.
INVALID_NAME = "__invalid__"


class GreeterServicer(helloworld_pb2_grpc.GreeterServicer):
    """결정론적 Greeter 구현.

    - name 이 비어 있거나 sentinel 이면 INVALID_ARGUMENT 로 abort
      (백엔드 측 검증 시뮬레이션)
    - 정상이면 "Hello, {name}!" 응답
    """

    def SayHello(self, request, context):
        if not request.name or request.name == INVALID_NAME:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "invalid name")
        return helloworld_pb2.HelloReply(message=f"Hello, {request.name}!")


def _start_server(servicer) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    helloworld_pb2_grpc.add_GreeterServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    return server


@pytest.fixture
def grpc_server():
    """결정론적 Greeter 서버를 띄우고 테스트 종료 시 정리한다."""
    server = _start_server(GreeterServicer())
    yield server
    server.stop(grace=None)
