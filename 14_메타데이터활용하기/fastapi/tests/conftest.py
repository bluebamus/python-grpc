"""통합 테스트용 픽스처.

실제 gRPC 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 그 서버를
호출하도록 한다. 이 예제의 주제는 메타데이터이므로, 서비서는 수신한
메타데이터를 **결정론적으로** 응답 trailing metadata 로 되돌려준다:

- 수신한 `x-request-id` 를 그대로 trailing `x-request-id` 로 반환 (왕복 증명)
- `authorization` 메타데이터의 존재 여부를 `x-auth-present`("true"/"false")로 반환

배정 포트(50064)만 사용한다.
"""

from concurrent import futures

import grpc
import pytest

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import metadata_example_pb2
import metadata_example_pb2_grpc

GRPC_PORT = 50064
GRPC_TARGET = f"localhost:{GRPC_PORT}"


class EchoServicer(metadata_example_pb2_grpc.EchoServiceServicer):
    """수신 메타데이터를 읽어 응답 trailing metadata 로 되돌려주는 서비서."""

    def Echo(self, request, context):
        metadata = dict(context.invocation_metadata())
        request_id = metadata.get("x-request-id", "")
        auth_present = "true" if metadata.get("authorization") else "false"

        # 수신 메타데이터를 응답 trailing metadata 로 되돌린다(왕복 증명).
        context.set_trailing_metadata(
            (
                ("x-request-id", request_id),
                ("x-auth-present", auth_present),
            )
        )
        # 메시지는 단순 echo.
        return metadata_example_pb2.EchoResponse(message=f"Echo: {request.message}")


def _start_server() -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    metadata_example_pb2_grpc.add_EchoServiceServicer_to_server(EchoServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    return server


@pytest.fixture
def grpc_server():
    """배정 포트(50064)로 결정론적 Echo 서버를 띄운다. 테스트 종료 시 정리."""
    server = _start_server()
    yield server
    server.stop(grace=None)
