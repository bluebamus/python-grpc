"""gRPC 클라이언트 래퍼 (Django).

FastAPI 샘플과 동일한 원리. 게이트웨이는 두 종류의 gRPC 호출을 한다.

1. Echo(EchoRequest) — 평범한 unary 비즈니스 호출.
2. list_services — 서버 리플렉션으로 서버가 노출하는 서비스 목록을 조회한다.
   클라이언트가 .proto 를 미리 갖고 있지 않아도, 서버에 직접 물어 발견할 수 있다.

채널은 비싸므로 모듈 레벨에서 한 번 만들어 재사용한다(get_client).
설정값은 Django settings 에서 읽는다.
"""

import grpc
from django.conf import settings
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc

from gateway import proto  # noqa: F401  (sys.path 등록)
import reflection_example_pb2
import reflection_example_pb2_grpc


class GrpcClient:
    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.GRPC_TARGET
        self._channel = grpc.insecure_channel(self._target)
        self._echo_stub = reflection_example_pb2_grpc.EchoServiceStub(self._channel)
        # 리플렉션도 결국 채널 위에서 동작하는 또 하나의 gRPC 서비스다.
        self._reflection_stub = reflection_pb2_grpc.ServerReflectionStub(self._channel)

    def echo(self, message: str, timeout: float = 5.0) -> str:
        request = reflection_example_pb2.EchoRequest(message=message)
        response = self._echo_stub.Echo(request, timeout=timeout)
        return response.message

    def list_services(self, timeout: float = 5.0) -> list[str]:
        """서버 리플렉션으로 노출된 서비스 전체 이름 목록을 조회한다.

        list_services="*" 는 "모든 서비스를 나열하라"는 표준 관례다.
        리플렉션은 양방향 스트리밍 RPC 이므로, 단일 요청도 이터레이터로 감싼다.
        """
        request = reflection_pb2.ServerReflectionRequest(list_services="*")
        responses = self._reflection_stub.ServerReflectionInfo(iter([request]), timeout=timeout)
        names: list[str] = []
        for response in responses:
            for service in response.list_services_response.service:
                names.append(service.name)
        return names


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
