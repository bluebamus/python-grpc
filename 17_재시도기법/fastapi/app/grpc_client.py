"""gRPC 클라이언트 래퍼.

이 예제(17_재시도기법)의 핵심은 채널에 재시도 정책을 주입하는 것이다.
백엔드가 일시적으로 UNAVAILABLE 을 반환해도, gRPC 런타임이 service_config
에 정의된 정책에 따라 자동으로 재시도한다. 애플리케이션 코드에는 재시도
루프가 전혀 없다는 점이 포인트다.
"""

import json

import grpc

from app.config import settings

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import example_pb2
import example_pb2_grpc


def _service_config() -> str:
    """채널에 주입할 service_config(JSON 문자열)을 만든다."""
    retry_policy = {
        "maxAttempts": settings.retry_max_attempts,
        "initialBackoff": settings.retry_initial_backoff,
        "maxBackoff": settings.retry_max_backoff,
        "backoffMultiplier": settings.retry_backoff_multiplier,
        "retryableStatusCodes": ["UNAVAILABLE"],
    }
    # name 의 빈 객체 [{}] 는 "모든 메서드에 적용"을 의미한다.
    return json.dumps({"methodConfig": [{"name": [{}], "retryPolicy": retry_policy}]})


def _channel_options() -> list[tuple[str, object]]:
    return [
        ("grpc.enable_retries", 1),
        ("grpc.service_config", _service_config()),
    ]


class GrpcClient:
    """게이트웨이 수명 동안 재사용하는 채널/스텁 보관 객체.

    채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
    """

    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._channel: grpc.Channel | None = None
        self._stub: example_pb2_grpc.ExampleServiceStub | None = None

    def connect(self) -> None:
        self._channel = grpc.insecure_channel(self._target, options=_channel_options())
        self._stub = example_pb2_grpc.ExampleServiceStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    def unary_call(self, message: str, timeout: float = 5.0) -> str:
        """UnaryCall 호출. 재시도는 채널이 자동 처리한다.

        timeout 은 '재시도 전체'에 대한 데드라인이다(개별 시도가 아님).
        """
        if self._stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        request = example_pb2.ExampleRequest(message=message)
        response = self._stub.UnaryCall(request, timeout=timeout)
        return response.message
