"""Django 통합 테스트용 픽스처.

FastAPI 샘플과 동일하게, 이 예제의 주제(서버 리플렉션)를 검증하기 위해
테스트 gRPC 서버에도 `reflection.enable_server_reflection` 로 리플렉션을
켠 뒤 백그라운드로 띄운다. 결정론적 Echo 서비서를 직접 작성한다.
"""

from concurrent import futures

import grpc
import pytest
from grpc_reflection.v1alpha import reflection

from gateway import proto  # noqa: F401
import reflection_example_pb2
import reflection_example_pb2_grpc
from gateway import grpc_client

GRPC_PORT = 50062


class EchoServicer(reflection_example_pb2_grpc.EchoServiceServicer):
    """요청 message 를 그대로 돌려주는 결정론적 Echo 서비서."""

    def Echo(self, request, context):
        return reflection_example_pb2.EchoResponse(message=request.message)


@pytest.fixture
def grpc_server():
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

    # 각 테스트마다 채널을 새로 만들어 이전 상태가 새지 않게 한다.
    grpc_client.reset_client()
    yield server
    grpc_client.reset_client()
    server.stop(grace=None)
