"""gRPC 클라이언트 래퍼.

이 예제(10_에러핸들링)의 핵심은 "게이트웨이에서의 에러 변환"이다.
gRPC 서버는 divisor=0 같은 잘못된 입력에 대해 INVALID_ARGUMENT 로 abort
한다. 클라이언트 래퍼는 그 RpcError 를 그대로 위로 던지고, 상위 계층
(main.py)이 gRPC StatusCode 를 HTTP 상태코드로 매핑한다.

채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
"""

import grpc

from app.config import settings

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import error_handling_example_pb2 as pb2
import error_handling_example_pb2_grpc as pb2_grpc


class GrpcClient:
    """게이트웨이 수명 동안 재사용하는 채널/스텁 보관 객체."""

    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._channel: grpc.Channel | None = None
        self._stub: pb2_grpc.CalculatorStub | None = None

    def connect(self) -> None:
        self._channel = grpc.insecure_channel(self._target)
        self._stub = pb2_grpc.CalculatorStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    def divide(self, dividend: float, divisor: float, timeout: float = 5.0) -> float:
        """Divide 호출.

        divisor 가 0 이면 서버가 INVALID_ARGUMENT 로 abort 하고, 이는
        grpc.RpcError 로 표면화된다. 여기서는 잡지 않고 그대로 전파해
        호출자가 상태코드를 보고 HTTP 로 매핑하게 한다.
        """
        if self._stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        request = pb2.DivideRequest(dividend=dividend, divisor=divisor)
        response = self._stub.Divide(request, timeout=timeout)
        return response.quotient
