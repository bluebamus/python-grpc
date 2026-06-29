"""gRPC 클라이언트 래퍼 (Django).

FastAPI 샘플과 동일한 원리: 호출마다 per-call 데드라인(timeout)을 적용한다.
채널은 비싸므로 모듈 레벨에서 한 번 만들어 재사용한다(get_client).
설정값은 Django settings 에서 읽는다.

동기 WSGI 환경에서는 브라우저 연결 끊김을 즉시 감지하기 어렵기 때문에,
이 샘플은 per-call 데드라인으로 자원 사용 상한을 두는 방식에 집중한다.
데드라인을 넘기면 gRPC 가 DEADLINE_EXCEEDED 를 던지고 서버 작업도 취소된다.
"""

import grpc
from django.conf import settings

from gateway import proto  # noqa: F401  (sys.path 등록)
import cancel_example_pb2
import cancel_example_pb2_grpc


class GrpcClient:
    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.GRPC_TARGET
        self._channel = grpc.insecure_channel(self._target)
        self._stub = cancel_example_pb2_grpc.CancelServiceStub(self._channel)

    def long_running_operation(self, data: str, timeout: float) -> str:
        """per-call 데드라인을 걸어 LongRunningOperation 을 호출한다.

        timeout(초) 초과 시 grpc.RpcError(DEADLINE_EXCEEDED) 가 발생한다.
        """
        request = cancel_example_pb2.Request(request_data=data)
        response = self._stub.LongRunningOperation(request, timeout=timeout)
        return response.response_data


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
