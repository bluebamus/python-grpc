"""gRPC 헬스체크 클라이언트 래퍼 (Django).

FastAPI 샘플과 동일한 원리: 표준 헬스체크(`grpc.health.v1.health/Check`)를 호출해
백엔드 서비스의 서빙 상태를 가져온다. 채널은 비싸므로 모듈 레벨에서 한 번
만들어 재사용한다(get_client). 설정값은 Django settings 에서 읽는다.
"""

import grpc
from django.conf import settings

from gateway import proto  # noqa: F401  (sys.path 등록)
import health_check_pb2
import health_check_pb2_grpc


class GrpcClient:
    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.GRPC_TARGET
        self._channel = grpc.insecure_channel(self._target)
        self._stub = health_check_pb2_grpc.healthStub(self._channel)

    def check(self, service: str, timeout: float | None = None) -> int:
        """헬스체크 Check 호출. 반환값은 ServingStatus(int)."""
        request = health_check_pb2.HealthCheckRequest(service=service)
        response = self._stub.Check(
            request, timeout=timeout or settings.GRPC_HEALTH_TIMEOUT
        )
        return response.status


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
