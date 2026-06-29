"""통합 테스트용 픽스처.

실제 gRPC 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 그 서버를
호출하도록 한다. test 서비서는 결정론적으로 동작하며, 수신 메타데이터에서
`x-request-id` 를 읽어 trailing metadata 로 되돌려준다. 이를 통해 클라이언트
인터셉터가 주입한 메타데이터가 실제로 서버까지 전달되었는지 검증할 수 있다.
"""

import threading
from concurrent import futures

import grpc
import pytest

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import interceptor_example_pb2
import interceptor_example_pb2_grpc

# 9_인터셉터 예제에 배정된 고유 포트
GRPC_PORT = 50059
GRPC_TARGET = f"localhost:{GRPC_PORT}"

_REQUEST_ID_KEY = "x-request-id"


class EchoServicer(interceptor_example_pb2_grpc.EchoServiceServicer):
    """받은 메시지를 그대로 echo 한다.

    추가로 수신 메타데이터에서 x-request-id 를 읽어 (1) 기록하고
    (2) trailing metadata 로 되돌려준다.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.received_request_ids: list[str] = []

    def Echo(self, request, context):
        metadata = dict(context.invocation_metadata())
        request_id = metadata.get(_REQUEST_ID_KEY, "")
        with self._lock:
            self.received_request_ids.append(request_id)
        # 인터셉터가 주입한 값을 그대로 클라이언트에 돌려준다(echo back).
        context.set_trailing_metadata(((_REQUEST_ID_KEY, request_id),))
        return interceptor_example_pb2.EchoResponse(message=request.message)


def _start_server(servicer) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    interceptor_example_pb2_grpc.add_EchoServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    return server


@pytest.fixture
def echo_server():
    """test 서비서를 띄우고, 테스트 종료 시 정리한다."""
    servicer = EchoServicer()
    server = _start_server(servicer)
    try:
        yield servicer
    finally:
        server.stop(grace=None)
