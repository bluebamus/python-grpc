"""통합 테스트용 픽스처.

실제 gRPC 헬스체크 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 그
서버를 호출하도록 한다. 헬스체크 동작을 결정론적으로 검증하기 위해, 서비스명별
ServingStatus 를 미리 지정해 둔 서비서를 사용한다(random/input 없음).
"""

from concurrent import futures

import grpc
import pytest

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import health_check_pb2
import health_check_pb2_grpc

GRPC_PORT = 50061
GRPC_TARGET = f"localhost:{GRPC_PORT}"

_Status = health_check_pb2.HealthCheckResponse


class HealthServicer(health_check_pb2_grpc.healthServicer):
    """서비스명 -> ServingStatus 매핑을 그대로 돌려주는 결정론적 서비서.

    매핑에 없는 이름은 SERVICE_UNKNOWN 을 반환한다(표준 health 프로토콜 관례).
    빈 문자열("")은 "서버 전체"를 의미하므로 기본 SERVING 으로 둔다.
    """

    def __init__(self, statuses: dict[str, int]) -> None:
        self._statuses = statuses

    def Check(self, request, context):
        status = self._statuses.get(request.service, _Status.SERVICE_UNKNOWN)
        return health_check_pb2.HealthCheckResponse(status=status)


def _start_server(servicer) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    health_check_pb2_grpc.add_healthServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    return server


@pytest.fixture
def grpc_server_factory():
    """서비스명->상태 매핑을 지정해 서버를 띄우는 팩토리. 테스트 종료 시 정리."""
    servers: list[grpc.Server] = []

    def _make(statuses: dict[str, int]) -> HealthServicer:
        servicer = HealthServicer(statuses)
        servers.append(_start_server(servicer))
        return servicer

    yield _make

    for s in servers:
        s.stop(grace=None)
