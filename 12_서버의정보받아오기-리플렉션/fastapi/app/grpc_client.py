"""gRPC 클라이언트 래퍼.

이 예제(12_서버의정보받아오기-리플렉션)의 핵심은 **서버 리플렉션**이다.
게이트웨이는 두 가지 호출을 한다.

1. Echo(EchoRequest) — 평범한 unary 비즈니스 호출.
2. list_services — 서버가 노출하는 서비스 목록을 리플렉션으로 조회한다.
   클라이언트가 .proto 파일을 미리 갖고 있지 않아도, 서버에 직접 물어서
   "어떤 서비스가 있는지" 알아낼 수 있다는 점이 리플렉션의 포인트다.

리플렉션은 표준 양방향 스트리밍 RPC(`ServerReflectionInfo`)로 동작한다.
여기서는 `ServerReflectionStub` 에 `ServerReflectionRequest(list_services="*")`
를 보내고 응답 스트림에서 서비스 이름을 파싱한다.
"""

import grpc
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc

from app.config import settings

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import reflection_example_pb2
import reflection_example_pb2_grpc


class GrpcClient:
    """게이트웨이 수명 동안 재사용하는 채널/스텁 보관 객체.

    채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
    """

    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._channel: grpc.Channel | None = None
        self._echo_stub: reflection_example_pb2_grpc.EchoServiceStub | None = None
        self._reflection_stub: reflection_pb2_grpc.ServerReflectionStub | None = None

    def connect(self) -> None:
        self._channel = grpc.insecure_channel(self._target)
        self._echo_stub = reflection_example_pb2_grpc.EchoServiceStub(self._channel)
        # 리플렉션도 결국 채널 위에서 동작하는 또 하나의 gRPC 서비스다.
        self._reflection_stub = reflection_pb2_grpc.ServerReflectionStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._echo_stub = None
            self._reflection_stub = None

    def echo(self, message: str, timeout: float = 5.0) -> str:
        """Echo 호출. 요청 message 를 그대로 돌려받는다."""
        if self._echo_stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        request = reflection_example_pb2.EchoRequest(message=message)
        response = self._echo_stub.Echo(request, timeout=timeout)
        return response.message

    def list_services(self, timeout: float = 5.0) -> list[str]:
        """서버 리플렉션으로 노출된 서비스 전체 이름 목록을 조회한다.

        list_services="*" 는 "모든 서비스를 나열하라"는 표준 관례다.
        응답은 스트림으로 오므로 첫 응답에서 service 목록을 추출한다.
        """
        if self._reflection_stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        request = reflection_pb2.ServerReflectionRequest(list_services="*")
        # 단일 요청을 이터레이터로 감싸 양방향 스트리밍 RPC 에 전달한다.
        responses = self._reflection_stub.ServerReflectionInfo(iter([request]), timeout=timeout)
        names: list[str] = []
        for response in responses:
            for service in response.list_services_response.service:
                names.append(service.name)
        return names
