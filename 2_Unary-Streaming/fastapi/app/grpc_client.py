"""gRPC 클라이언트 래퍼.

이 예제(2_Unary-Streaming)의 게이트웨이는 가장 기본적인 Unary RPC 인
`Greeter.SayHello` 를 호출한다. 채널은 비싸므로 요청마다 새로 만들지 않고
앱 수명 동안 한 번 만들어 재사용한다.
"""

import grpc

from app.config import settings

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import helloworld_pb2
import helloworld_pb2_grpc


class GrpcClient:
    """게이트웨이 수명 동안 재사용하는 채널/스텁 보관 객체.

    채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
    """

    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._channel: grpc.Channel | None = None
        self._stub: helloworld_pb2_grpc.GreeterStub | None = None

    def connect(self) -> None:
        self._channel = grpc.insecure_channel(self._target)
        self._stub = helloworld_pb2_grpc.GreeterStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    def say_hello(self, name: str, timeout: float = 5.0) -> str:
        """SayHello 호출. HelloRequest(name) -> HelloReply(message)."""
        if self._stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        request = helloworld_pb2.HelloRequest(name=name)
        response = self._stub.SayHello(request, timeout=timeout)
        return response.message
