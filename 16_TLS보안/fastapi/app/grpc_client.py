"""gRPC 클라이언트 래퍼 (TLS 보안 채널).

이 예제(16_TLS보안)의 핵심은 평문(insecure)이 아니라 TLS 로 백엔드에
연결하는 것이다. `grpc.secure_channel` + `grpc.ssl_channel_credentials`
로 서버 인증서를 검증한 뒤에야 RPC 가 흐른다. 인증서 검증에 실패하면
핸드셰이크 단계에서 막혀 RPC 자체가 시작되지 못한다.

자체서명 인증서를 쓰면 호스트네임 검증 문제가 날 수 있는데, 그때는
채널 옵션 `grpc.ssl_target_name_override` 로 검증 대상 이름을 인증서의
CN/SAN 값으로 바꿔준다(설정에서 분리).
"""

import grpc

from app.config import settings

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import example_pb2
import example_pb2_grpc


def _load_credentials() -> grpc.ChannelCredentials:
    """루트 인증서를 읽어 TLS 채널 자격증명을 만든다."""
    with open(settings.grpc_root_cert, "rb") as f:
        root_certificates = f.read()
    return grpc.ssl_channel_credentials(root_certificates=root_certificates)


def _channel_options() -> list[tuple[str, object]]:
    options: list[tuple[str, object]] = []
    override = settings.grpc_ssl_target_name_override
    if override:
        # 자체서명 인증서의 CN/SAN 과 접속 호스트가 다를 때 검증을 통과시킨다.
        options.append(("grpc.ssl_target_name_override", override))
    return options


class GrpcClient:
    """게이트웨이 수명 동안 재사용하는 TLS 채널/스텁 보관 객체.

    채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
    """

    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._channel: grpc.Channel | None = None
        self._stub: example_pb2_grpc.ExampleServiceStub | None = None

    def connect(self) -> None:
        credentials = _load_credentials()
        # 평문(insecure_channel)이 아니라 보안 채널을 연다.
        self._channel = grpc.secure_channel(
            self._target, credentials, options=_channel_options()
        )
        self._stub = example_pb2_grpc.ExampleServiceStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    def say_hello(self, name: str, timeout: float = 5.0) -> str:
        """SayHello 단항 호출. TLS 핸드셰이크는 첫 호출 시 자동으로 일어난다."""
        if self._stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        request = example_pb2.HelloRequest(name=name)
        response = self._stub.SayHello(request, timeout=timeout)
        return response.message
