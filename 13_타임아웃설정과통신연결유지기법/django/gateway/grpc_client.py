"""gRPC 클라이언트 래퍼 (Django).

FastAPI 샘플과 동일한 원리:
1. 채널에 **keepalive 옵션**을 주입해 장수명 연결을 살린다.
2. 호출마다 **per-call deadline(timeout)** 을 적용한다.
채널은 비싸므로 모듈 레벨에서 한 번 만들어 재사용한다(get_client).
설정값은 Django settings 에서 읽는다.
"""

import grpc
from django.conf import settings

from gateway import proto  # noqa: F401  (sys.path 등록)
import wait_example_pb2
import wait_example_pb2_grpc


def _channel_options() -> list[tuple[str, object]]:
    """채널에 주입할 keepalive 옵션."""
    return [
        ("grpc.keepalive_time_ms", settings.GRPC_KEEPALIVE_TIME_MS),
        ("grpc.keepalive_timeout_ms", settings.GRPC_KEEPALIVE_TIMEOUT_MS),
        ("grpc.keepalive_permit_without_calls", settings.GRPC_KEEPALIVE_PERMIT_WITHOUT_CALLS),
        ("grpc.http2.max_pings_without_data", settings.GRPC_HTTP2_MAX_PINGS_WITHOUT_DATA),
    ]


class GrpcClient:
    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.GRPC_TARGET
        self._channel = grpc.insecure_channel(self._target, options=_channel_options())
        self._stub = wait_example_pb2_grpc.EchoServiceStub(self._channel)

    def echo(self, message: str, deadline_ms: int | None = None) -> str:
        """Echo 호출에 per-call deadline 을 적용한다.

        deadline_ms 가 None 이면 설정 기본값을 쓴다. gRPC timeout 은 초 단위
        float 이므로 ms 를 환산한다. 데드라인 초과 시 DEADLINE_EXCEEDED 발생.
        """
        if deadline_ms is None:
            deadline_ms = settings.GRPC_DEFAULT_DEADLINE_MS
        timeout_s = deadline_ms / 1000.0
        request = wait_example_pb2.EchoRequest(message=message)
        response = self._stub.Echo(request, timeout=timeout_s)
        return response.message


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
