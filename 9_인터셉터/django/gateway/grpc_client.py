"""gRPC 클라이언트 래퍼 + 클라이언트 인터셉터 (Django).

FastAPI 샘플과 동일한 원리: `grpc.UnaryUnaryClientInterceptor` 를 직접 구현해
채널에 씌운다. 인터셉터는 (1) 호출 시작/종료 로깅, (2) `x-request-id`
메타데이터 자동 주입, (3) 실행 증거용 호출 카운트를 담당한다.
채널은 비싸므로 모듈 레벨에서 한 번 만들어 재사용한다(get_client).
"""

import logging
import threading
import uuid
from collections import namedtuple

import grpc
from django.conf import settings

from gateway import proto  # noqa: F401  (sys.path 등록)
import interceptor_example_pb2
import interceptor_example_pb2_grpc

logger = logging.getLogger("gateway.interceptor")

_REQUEST_ID_KEY = "x-request-id"


class _ClientCallDetails(
    namedtuple(
        "_ClientCallDetails",
        ("method", "timeout", "metadata", "credentials", "wait_for_ready", "compression"),
    ),
    grpc.ClientCallDetails,
):
    """grpc.ClientCallDetails 는 불변이라 메타데이터 추가 시 새 객체로 교체한다."""


class LoggingRequestIdInterceptor(grpc.UnaryUnaryClientInterceptor):
    """unary-unary 호출을 가로채는 클라이언트 인터셉터.

    책임: 로깅, x-request-id 자동 주입, 호출 카운트 증가(실행 증거).
    """

    def __init__(self) -> None:
        self._call_count = 0
        self._lock = threading.Lock()

    @property
    def call_count(self) -> int:
        return self._call_count

    def intercept_unary_unary(self, continuation, client_call_details, request):
        # --- x-request-id 자동 주입 ---
        metadata = list(client_call_details.metadata or [])
        has_request_id = any(key.lower() == _REQUEST_ID_KEY for key, _ in metadata)
        if not has_request_id:
            request_id = uuid.uuid4().hex
            metadata.append((_REQUEST_ID_KEY, request_id))
        else:
            request_id = next(v for k, v in metadata if k.lower() == _REQUEST_ID_KEY)

        new_details = _ClientCallDetails(
            client_call_details.method,
            client_call_details.timeout,
            metadata,
            client_call_details.credentials,
            client_call_details.wait_for_ready,
            client_call_details.compression,
        )

        # --- 호출 카운트 증가 (인터셉터 실행 증거) ---
        with self._lock:
            self._call_count += 1

        # --- 시작/종료 로깅 ---
        logger.info(
            "gRPC 호출 시작 method=%s %s=%s", client_call_details.method, _REQUEST_ID_KEY, request_id
        )
        response = continuation(new_details, request)
        logger.info(
            "gRPC 호출 종료 method=%s %s=%s", client_call_details.method, _REQUEST_ID_KEY, request_id
        )
        return response


class GrpcClient:
    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.GRPC_TARGET
        self.interceptor = LoggingRequestIdInterceptor()
        base_channel = grpc.insecure_channel(self._target)
        self._channel = grpc.intercept_channel(base_channel, self.interceptor)
        self._stub = interceptor_example_pb2_grpc.EchoServiceStub(self._channel)

    def echo(self, message: str, timeout: float = 5.0) -> tuple[str, str]:
        """Echo 호출. 응답 메시지와 서버가 되돌려준 x-request-id 를 함께 반환한다."""
        request = interceptor_example_pb2.EchoRequest(message=message)
        response, call = self._stub.Echo.with_call(request, timeout=timeout)
        request_id = ""
        for key, value in call.trailing_metadata() or ():
            if key.lower() == _REQUEST_ID_KEY:
                request_id = value
                break
        return response.message, request_id


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
