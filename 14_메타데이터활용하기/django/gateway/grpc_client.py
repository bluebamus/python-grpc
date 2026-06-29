"""gRPC 클라이언트 래퍼 (Django).

FastAPI 샘플과 동일한 원리: **HTTP 헤더에서 온 값을 gRPC 메타데이터로
변환해 주입**하고, 서버가 trailing metadata 로 되돌려준 값을 다시 읽는다.

- 메타데이터 키는 소문자여야 한다(gRPC 규약).
  HTTP 헤더 `Authorization` / `X-Request-Id` → `authorization` / `x-request-id`.
- 채널은 비싸므로 모듈 레벨에서 한 번 만들어 재사용한다(get_client).
- 설정값은 Django settings 에서 읽는다.
"""

import grpc
from django.conf import settings

from gateway import proto  # noqa: F401  (sys.path 등록)
import metadata_example_pb2
import metadata_example_pb2_grpc


class EchoResult:
    """게이트웨이가 서버로부터 받은 결과 묶음."""

    def __init__(self, message: str, request_id: str, auth_present: str) -> None:
        self.message = message
        self.request_id = request_id
        self.auth_present = auth_present


class GrpcClient:
    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.GRPC_TARGET
        self._channel = grpc.insecure_channel(self._target)
        self._stub = metadata_example_pb2_grpc.EchoServiceStub(self._channel)

    def echo(
        self,
        message: str,
        request_id: str,
        authorization: str | None = None,
        timeout: float | None = None,
    ) -> EchoResult:
        # --- HTTP 헤더 -> gRPC 메타데이터 변환 ---
        metadata: list[tuple[str, str]] = [("x-request-id", request_id)]
        if authorization:
            metadata.append(("authorization", authorization))

        request = metadata_example_pb2.EchoRequest(message=message)
        response, call = self._stub.Echo.with_call(
            request,
            metadata=tuple(metadata),
            timeout=timeout if timeout is not None else settings.GRPC_TIMEOUT,
        )

        # --- 서버가 보낸 trailing 메타데이터 읽기 ---
        trailing = dict(call.trailing_metadata())
        returned_request_id = trailing.get("x-request-id", request_id)
        auth_present = trailing.get("x-auth-present", "false")

        return EchoResult(
            message=response.message,
            request_id=returned_request_id,
            auth_present=auth_present,
        )


_client: GrpcClient | None = None


def get_client() -> GrpcClient:
    """프로세스 단위로 재사용되는 클라이언트를 반환한다."""
    global _client
    if _client is None:
        _client = GrpcClient()
    return _client


def reset_client() -> None:
    """테스트에서 채널을 다시 만들고 싶을 때 사용."""
    global _client
    _client = None
