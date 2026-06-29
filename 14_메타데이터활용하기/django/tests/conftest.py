"""Django 통합 테스트용 픽스처.

FastAPI 샘플과 동일하게, 결정론적 메타데이터 왕복 검증을 위해 수신
메타데이터를 응답 trailing metadata 로 되돌려주는 gRPC 서버를 백그라운드로
띄운다:

- 수신한 `x-request-id` 를 그대로 trailing `x-request-id` 로 반환 (왕복 증명)
- `authorization` 메타데이터의 존재 여부를 `x-auth-present`("true"/"false")로 반환

배정 포트(50064)만 사용한다.
"""

from concurrent import futures

import grpc
import pytest

from gateway import proto  # noqa: F401
import metadata_example_pb2
import metadata_example_pb2_grpc
from gateway import grpc_client

GRPC_PORT = 50064


class EchoServicer(metadata_example_pb2_grpc.EchoServiceServicer):
    """수신 메타데이터를 읽어 응답 trailing metadata 로 되돌려주는 서비서."""

    def Echo(self, request, context):
        metadata = dict(context.invocation_metadata())
        request_id = metadata.get("x-request-id", "")
        auth_present = "true" if metadata.get("authorization") else "false"

        context.set_trailing_metadata(
            (
                ("x-request-id", request_id),
                ("x-auth-present", auth_present),
            )
        )
        return metadata_example_pb2.EchoResponse(message=f"Echo: {request.message}")


@pytest.fixture
def grpc_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    metadata_example_pb2_grpc.add_EchoServiceServicer_to_server(EchoServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()

    # 각 테스트마다 채널을 새로 만들어 이전 서버에 대한 연결 상태가 새지 않게 한다.
    grpc_client.reset_client()
    yield server
    grpc_client.reset_client()

    server.stop(grace=None)
