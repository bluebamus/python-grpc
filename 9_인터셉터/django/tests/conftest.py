"""Django 통합 테스트용 픽스처.

FastAPI 샘플과 동일하게, 결정론적 검증을 위해 받은 메시지를 그대로 echo 하고
수신 메타데이터의 x-request-id 를 trailing metadata 로 되돌려주는 gRPC 서버를
백그라운드로 띄운다.
"""

import threading
from concurrent import futures

import grpc
import pytest

from gateway import proto  # noqa: F401
import interceptor_example_pb2
import interceptor_example_pb2_grpc
from gateway import grpc_client

# 9_인터셉터 예제에 배정된 고유 포트
GRPC_PORT = 50059

_REQUEST_ID_KEY = "x-request-id"


class EchoServicer(interceptor_example_pb2_grpc.EchoServiceServicer):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.received_request_ids: list[str] = []

    def Echo(self, request, context):
        metadata = dict(context.invocation_metadata())
        request_id = metadata.get(_REQUEST_ID_KEY, "")
        with self._lock:
            self.received_request_ids.append(request_id)
        context.set_trailing_metadata(((_REQUEST_ID_KEY, request_id),))
        return interceptor_example_pb2.EchoResponse(message=request.message)


@pytest.fixture
def echo_server():
    servicer = EchoServicer()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    interceptor_example_pb2_grpc.add_EchoServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()

    # 각 테스트마다 채널을 새로 만들어 이전 서버에 대한 연결 상태가 새지 않게 한다.
    grpc_client.reset_client()
    try:
        yield servicer
    finally:
        grpc_client.reset_client()
        server.stop(grace=None)
