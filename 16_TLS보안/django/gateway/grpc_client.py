"""gRPC 클라이언트 래퍼 (Django, TLS 보안 채널).

FastAPI 샘플과 동일한 원리: 평문이 아니라 `grpc.secure_channel` +
`grpc.ssl_channel_credentials` 로 서버 인증서를 검증한 뒤에만 RPC 가 흐른다.
채널은 비싸므로 모듈 레벨에서 한 번 만들어 재사용한다(get_client).
설정값은 Django settings 에서 읽는다.
"""

import grpc
from django.conf import settings

from gateway import proto  # noqa: F401  (sys.path 등록)
import example_pb2
import example_pb2_grpc


def _load_credentials() -> grpc.ChannelCredentials:
    with open(settings.GRPC_ROOT_CERT, "rb") as f:
        root_certificates = f.read()
    return grpc.ssl_channel_credentials(root_certificates=root_certificates)


def _channel_options() -> list[tuple[str, object]]:
    options: list[tuple[str, object]] = []
    override = settings.GRPC_SSL_TARGET_NAME_OVERRIDE
    if override:
        # 자체서명 인증서의 CN/SAN 과 접속 호스트가 다를 때 검증을 통과시킨다.
        options.append(("grpc.ssl_target_name_override", override))
    return options


class GrpcClient:
    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.GRPC_TARGET
        credentials = _load_credentials()
        # 평문(insecure_channel)이 아니라 보안 채널을 연다.
        self._channel = grpc.secure_channel(
            self._target, credentials, options=_channel_options()
        )
        self._stub = example_pb2_grpc.ExampleServiceStub(self._channel)

    def say_hello(self, name: str, timeout: float = 5.0) -> str:
        request = example_pb2.HelloRequest(name=name)
        response = self._stub.SayHello(request, timeout=timeout)
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
