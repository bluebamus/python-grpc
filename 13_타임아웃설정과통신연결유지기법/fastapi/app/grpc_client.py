"""gRPC 클라이언트 래퍼.

이 예제(13_타임아웃설정과통신연결유지기법)의 핵심은 두 가지다.

1. 채널에 **keepalive 옵션**을 주입한다. 유휴 연결에도 주기적으로 PING 을
   보내 연결 생존을 확인하고, 죽은 연결을 빨리 감지/재연결한다. 장시간 열어두는
   gRPC 채널(게이트웨이 수명 동안 재사용)에서 특히 중요하다.
2. 호출 시 **per-call deadline(timeout)** 을 적용한다. 백엔드가 너무 오래
   걸리면 gRPC 런타임이 호출을 끊고 `DEADLINE_EXCEEDED` 를 던진다.
"""

import grpc

from app.config import settings

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import wait_example_pb2
import wait_example_pb2_grpc


def _channel_options() -> list[tuple[str, object]]:
    """채널에 주입할 keepalive 옵션.

    - grpc.keepalive_time_ms: PING 송신 주기
    - grpc.keepalive_timeout_ms: PING 응답 대기 한도
    - grpc.keepalive_permit_without_calls: 진행 중 호출이 없어도 PING 허용
    - grpc.http2.max_pings_without_data: 데이터 없이 보낼 수 있는 PING 상한
    """
    return [
        ("grpc.keepalive_time_ms", settings.keepalive_time_ms),
        ("grpc.keepalive_timeout_ms", settings.keepalive_timeout_ms),
        ("grpc.keepalive_permit_without_calls", settings.keepalive_permit_without_calls),
        ("grpc.http2.max_pings_without_data", settings.http2_max_pings_without_data),
    ]


class GrpcClient:
    """게이트웨이 수명 동안 재사용하는 채널/스텁 보관 객체.

    채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
    keepalive 덕분에 오래 유휴 상태였던 연결도 죽지 않고 유지된다.
    """

    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._channel: grpc.Channel | None = None
        self._stub: wait_example_pb2_grpc.EchoServiceStub | None = None

    def connect(self) -> None:
        self._channel = grpc.insecure_channel(self._target, options=_channel_options())
        self._stub = wait_example_pb2_grpc.EchoServiceStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    def echo(self, message: str, deadline_ms: int | None = None) -> str:
        """Echo 호출에 per-call deadline 을 적용한다.

        deadline_ms 가 None 이면 설정의 기본값을 쓴다. gRPC 의 timeout 인자는
        '초' 단위 float 이므로 ms 를 초로 환산한다. 데드라인을 넘기면 gRPC 가
        `DEADLINE_EXCEEDED` 를 던진다.
        """
        if self._stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        if deadline_ms is None:
            deadline_ms = settings.default_deadline_ms
        timeout_s = deadline_ms / 1000.0
        request = wait_example_pb2.EchoRequest(message=message)
        response = self._stub.Echo(request, timeout=timeout_s)
        return response.message
