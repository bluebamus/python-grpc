"""Django 통합 테스트용 픽스처.

FastAPI 샘플과 동일하게, 결정론적 헬스체크 검증을 위해 서비스명별
ServingStatus 를 미리 지정한 gRPC 헬스 서버를 백그라운드로 띄운다.
"""

from concurrent import futures

import grpc
import pytest

from gateway import proto  # noqa: F401
import health_check_pb2
import health_check_pb2_grpc
from gateway import grpc_client

GRPC_PORT = 50061

_Status = health_check_pb2.HealthCheckResponse


class HealthServicer(health_check_pb2_grpc.healthServicer):
    """서비스명 -> ServingStatus 매핑을 그대로 돌려주는 결정론적 서비서."""

    def __init__(self, statuses: dict[str, int]) -> None:
        self._statuses = statuses

    def Check(self, request, context):
        status = self._statuses.get(request.service, _Status.SERVICE_UNKNOWN)
        return health_check_pb2.HealthCheckResponse(status=status)


@pytest.fixture
def grpc_server_factory():
    servers: list[grpc.Server] = []

    def _make(statuses: dict[str, int]) -> HealthServicer:
        servicer = HealthServicer(statuses)
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        health_check_pb2_grpc.add_healthServicer_to_server(servicer, server)
        server.add_insecure_port(f"[::]:{GRPC_PORT}")
        server.start()
        servers.append(server)
        return servicer

    # 각 테스트마다 채널을 새로 만들어 이전 서버에 대한 연결 상태가 새지 않게 한다.
    grpc_client.reset_client()
    yield _make
    grpc_client.reset_client()

    for s in servers:
        s.stop(grace=None)
