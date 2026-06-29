"""게이트웨이 통합 테스트.

브라우저 대신 TestClient 로 REST 엔드포인트를 호출하고, 그 호출이 내부
gRPC 헬스체크 백엔드로 전달되어 ServingStatus 가 HTTP 상태코드로 매핑되는지
end-to-end 로 확인한다.
"""

from fastapi.testclient import TestClient

import health_check_pb2
from app.main import app

_Status = health_check_pb2.HealthCheckResponse


def test_self_health_is_200():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_grpc_health_serving_returns_200(grpc_server_factory):
    grpc_server_factory({"api": _Status.SERVING})
    with TestClient(app) as client:
        resp = client.get("/health/grpc", params={"service": "api"})
    assert resp.status_code == 200
    assert resp.json() == {"service": "api", "status": "SERVING"}


def test_grpc_health_not_serving_returns_503(grpc_server_factory):
    grpc_server_factory({"api": _Status.NOT_SERVING})
    with TestClient(app) as client:
        resp = client.get("/health/grpc", params={"service": "api"})
    assert resp.status_code == 503
    assert resp.json() == {"service": "api", "status": "NOT_SERVING"}


def test_grpc_health_unknown_service_returns_503(grpc_server_factory):
    # 매핑에 없는 서비스명 -> 서비서가 SERVICE_UNKNOWN 반환 -> 503
    grpc_server_factory({"api": _Status.SERVING})
    with TestClient(app) as client:
        resp = client.get("/health/grpc", params={"service": "does-not-exist"})
    assert resp.status_code == 503
    assert resp.json()["status"] == "SERVICE_UNKNOWN"


def test_grpc_health_empty_service_overall(grpc_server_factory):
    # 빈 서비스명("")은 서버 전체 상태. SERVING 으로 두면 200.
    grpc_server_factory({"": _Status.SERVING})
    with TestClient(app) as client:
        resp = client.get("/health/grpc")
    assert resp.status_code == 200
    assert resp.json() == {"service": "", "status": "SERVING"}
