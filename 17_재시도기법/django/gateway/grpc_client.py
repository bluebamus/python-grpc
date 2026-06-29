"""gRPC 클라이언트 래퍼 (Django).

FastAPI 샘플과 동일한 원리: 채널에 재시도 service_config 를 주입한다.
채널은 비싸므로 모듈 레벨에서 한 번 만들어 재사용한다(get_client).
설정값은 Django settings 에서 읽는다.
"""

import json

import grpc
from django.conf import settings

from gateway import proto  # noqa: F401  (sys.path 등록)
import example_pb2
import example_pb2_grpc


def _service_config() -> str:
    retry_policy = {
        "maxAttempts": settings.GRPC_RETRY_MAX_ATTEMPTS,
        "initialBackoff": settings.GRPC_RETRY_INITIAL_BACKOFF,
        "maxBackoff": settings.GRPC_RETRY_MAX_BACKOFF,
        "backoffMultiplier": settings.GRPC_RETRY_BACKOFF_MULTIPLIER,
        "retryableStatusCodes": ["UNAVAILABLE"],
    }
    return json.dumps({"methodConfig": [{"name": [{}], "retryPolicy": retry_policy}]})


def _channel_options() -> list[tuple[str, object]]:
    return [
        ("grpc.enable_retries", 1),
        ("grpc.service_config", _service_config()),
    ]


class GrpcClient:
    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.GRPC_TARGET
        self._channel = grpc.insecure_channel(self._target, options=_channel_options())
        self._stub = example_pb2_grpc.ExampleServiceStub(self._channel)

    def unary_call(self, message: str, timeout: float = 5.0) -> str:
        request = example_pb2.ExampleRequest(message=message)
        response = self._stub.UnaryCall(request, timeout=timeout)
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
