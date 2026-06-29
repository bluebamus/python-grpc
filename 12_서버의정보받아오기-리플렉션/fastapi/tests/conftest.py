"""통합 테스트용 픽스처.

실제 gRPC 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 그 서버를
호출하도록 한다. 이 예제의 주제(서버 리플렉션)를 검증하기 위해, 테스트
서버에도 `reflection.enable_server_reflection` 로 리플렉션을 켠다.

예제의 server.py 는 input()/무한 대기 등 테스트에 부적합하므로, 결정론적
서비서를 직접 작성한다.
"""

from concurrent import futures

import grpc
import pytest
from grpc_reflection.v1alpha import reflection

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import reflection_example_pb2
import reflection_example_pb2_grpc

GRPC_PORT = 50062
GRPC_TARGET = f"localhost:{GRPC_PORT}"


class EchoServicer(reflection_example_pb2_grpc.EchoServiceServicer):
    """요청 message 를 그대로 돌려주는 결정론적 Echo 서비서."""

    def Echo(self, request, context):
        return reflection_example_pb2.EchoResponse(message=request.message)


def _start_server() -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    reflection_example_pb2_grpc.add_EchoServiceServicer_to_server(EchoServicer(), server)

    # --- 서버 리플렉션 활성화 (이 예제의 핵심) ---
    service_names = (
        reflection_example_pb2.DESCRIPTOR.services_by_name["EchoService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    return server


@pytest.fixture
def grpc_server():
    """리플렉션이 켜진 Echo 서버를 띄우고 테스트 종료 시 정리한다."""
    server = _start_server()
    yield server
    server.stop(grace=None)
