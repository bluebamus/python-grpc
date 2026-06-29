"""gRPC 헬스체크 클라이언트 래퍼.

이 예제(11_서버상태체크-healthcheck)의 핵심은 표준 헬스체크 프로토콜
(`grpc.health.v1.health/Check`)을 게이트웨이가 호출해, 백엔드 서비스의
서빙 상태를 HTTP 로 노출하는 것이다. 쿠버네티스 등 오케스트레이터의
liveness/readiness probe 를 REST 로 바꿔주는 BFF 패턴이다.
"""

import grpc

from app.config import settings

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import health_check_pb2
import health_check_pb2_grpc


class GrpcClient:
    """게이트웨이 수명 동안 재사용하는 채널/스텁 보관 객체.

    채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
    """

    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._channel: grpc.Channel | None = None
        self._stub: health_check_pb2_grpc.healthStub | None = None

    def connect(self) -> None:
        self._channel = grpc.insecure_channel(self._target)
        self._stub = health_check_pb2_grpc.healthStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    def check(self, service: str, timeout: float | None = None) -> int:
        """헬스체크 Check 호출.

        반환값은 HealthCheckResponse.ServingStatus(int) 이다.
        (SERVING=1, NOT_SERVING=2, SERVICE_UNKNOWN=3, UNKNOWN=0)
        백엔드가 해당 service 를 모르면 gRPC NOT_FOUND 로 abort 하는 구현도
        있으므로, 호출 측(main.py)에서 RpcError 를 함께 처리한다.
        """
        if self._stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        request = health_check_pb2.HealthCheckRequest(service=service)
        response = self._stub.Check(
            request, timeout=timeout or settings.health_timeout
        )
        return response.status
