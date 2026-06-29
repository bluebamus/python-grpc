"""gRPC 클라이언트 래퍼 (Django).

FastAPI 샘플과 동일한 원리: Calculator 스텁으로 Divide 를 호출한다.
divisor=0 같은 잘못된 입력에 대해 서버는 INVALID_ARGUMENT 로 abort 하고,
그 RpcError 는 그대로 위로 전파되어 뷰가 HTTP 상태코드로 매핑한다.

채널은 비싸므로 모듈 레벨에서 한 번 만들어 재사용한다(get_client).
"""

import grpc
from django.conf import settings

from gateway import proto  # noqa: F401  (sys.path 등록)
import error_handling_example_pb2 as pb2
import error_handling_example_pb2_grpc as pb2_grpc


class GrpcClient:
    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.GRPC_TARGET
        self._channel = grpc.insecure_channel(self._target)
        self._stub = pb2_grpc.CalculatorStub(self._channel)

    def divide(self, dividend: float, divisor: float, timeout: float = 5.0) -> float:
        request = pb2.DivideRequest(dividend=dividend, divisor=divisor)
        response = self._stub.Divide(request, timeout=timeout)
        return response.quotient


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
