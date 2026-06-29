"""gRPC 클라이언트 래퍼 + 클라이언트 인터셉터.

이 예제(9_인터셉터)의 핵심은 **클라이언트 인터셉터**다.
`grpc.UnaryUnaryClientInterceptor` 를 직접 구현해 채널에 적용하면,
모든 unary 호출이 스텁 코드를 거치기 전에 가로채진다. 인터셉터는
횡단 관심사(cross-cutting concern)를 한 곳에 모으는 표준 메커니즘으로,
여기서는 (1) 호출 시작/종료 로깅, (2) `x-request-id` 메타데이터 자동 주입을
담당한다. 애플리케이션/비즈니스 코드에는 이런 보일러플레이트가 전혀
없다는 점이 포인트다.
"""

import logging
import threading
import uuid
from collections import namedtuple

import grpc

from app.config import settings

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
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
    """grpc.ClientCallDetails 는 불변(immutable)이라 직접 수정할 수 없다.

    메타데이터를 추가하려면 같은 필드를 가진 새 객체를 만들어야 하므로,
    namedtuple 로 교체용 구조체를 정의한다.
    """


class LoggingRequestIdInterceptor(grpc.UnaryUnaryClientInterceptor):
    """unary-unary 호출을 가로채는 클라이언트 인터셉터.

    책임:
      1. 호출 시작/종료를 로깅한다(관측성).
      2. 메타데이터에 `x-request-id` 가 없으면 자동으로 주입한다(분산 추적).
      3. 인터셉터가 실제로 실행되었음을 외부에서 확인할 수 있도록 호출
         횟수(`call_count`)를 스레드 안전하게 증가시킨다.
    """

    def __init__(self) -> None:
        self._call_count = 0
        self._lock = threading.Lock()

    @property
    def call_count(self) -> int:
        """지금까지 이 인터셉터가 가로챈 호출 수."""
        return self._call_count

    def intercept_unary_unary(self, continuation, client_call_details, request):
        # --- (2) x-request-id 자동 주입 ---
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

        # --- (3) 호출 카운트 증가 (인터셉터 실행 증거) ---
        with self._lock:
            self._call_count += 1

        # --- (1) 시작/종료 로깅 ---
        logger.info(
            "gRPC 호출 시작 method=%s %s=%s", client_call_details.method, _REQUEST_ID_KEY, request_id
        )
        response = continuation(new_details, request)
        logger.info(
            "gRPC 호출 종료 method=%s %s=%s", client_call_details.method, _REQUEST_ID_KEY, request_id
        )
        return response


class GrpcClient:
    """게이트웨이 수명 동안 재사용하는 채널/스텁 보관 객체.

    채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
    인터셉터는 `grpc.intercept_channel` 로 채널에 씌운다.
    """

    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._channel: grpc.Channel | None = None
        self._stub: interceptor_example_pb2_grpc.EchoServiceStub | None = None
        # 게이트웨이도 인터셉터 인스턴스를 들고 있어 call_count 등을 관측할 수 있다.
        self.interceptor = LoggingRequestIdInterceptor()

    def connect(self) -> None:
        base_channel = grpc.insecure_channel(self._target)
        # 인터셉터를 채널에 적용한다. 이후 이 채널의 모든 unary 호출이 가로채진다.
        self._channel = grpc.intercept_channel(base_channel, self.interceptor)
        self._stub = interceptor_example_pb2_grpc.EchoServiceStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    def echo(self, message: str, timeout: float = 5.0) -> tuple[str, str]:
        """Echo 호출. 응답 메시지와 사용된 x-request-id 를 함께 돌려준다.

        request_id 는 서버가 수신 메타데이터에서 읽어 trailing metadata 로
        되돌려준 값이다. 즉 인터셉터가 주입한 메타데이터가 실제로 서버까지
        전달되었음을 end-to-end 로 확인할 수 있다.
        """
        if self._stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        request = interceptor_example_pb2.EchoRequest(message=message)
        response, call = self._stub.Echo.with_call(request, timeout=timeout)
        request_id = ""
        for key, value in call.trailing_metadata() or ():
            if key.lower() == _REQUEST_ID_KEY:
                request_id = value
                break
        return response.message, request_id
