"""Django 통합 테스트용 픽스처.

결정론적으로 동작하는 Greeter 서버를 백그라운드로 띄운다. 예제의 server.py 는
학습용이라 그대로 쓰지 않고 test 서비서를 직접 작성한다.
"""

from concurrent import futures

import grpc
import pytest

from gateway import proto  # noqa: F401
import helloworld_pb2
import helloworld_pb2_grpc
from gateway import grpc_client

GRPC_PORT = 50052

# 백엔드 INVALID_ARGUMENT 매핑을 검증하기 위한 sentinel.
INVALID_NAME = "__invalid__"


class GreeterServicer(helloworld_pb2_grpc.GreeterServicer):
    """결정론적 Greeter 구현.

    - name 이 비어 있거나 sentinel 이면 INVALID_ARGUMENT 로 abort
    - 정상이면 "Hello, {name}!" 응답
    """

    def SayHello(self, request, context):
        if not request.name or request.name == INVALID_NAME:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "invalid name")
        return helloworld_pb2.HelloReply(message=f"Hello, {request.name}!")


@pytest.fixture
def grpc_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    helloworld_pb2_grpc.add_GreeterServicer_to_server(GreeterServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()

    # 각 테스트마다 채널을 새로 만들어 이전 서버 연결 상태가 새지 않게 한다.
    grpc_client.reset_client()
    yield server
    grpc_client.reset_client()
    server.stop(grace=None)
