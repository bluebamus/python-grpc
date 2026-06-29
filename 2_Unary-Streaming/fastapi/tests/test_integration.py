"""게이트웨이 통합 테스트.

브라우저 대신 TestClient 로 REST 엔드포인트를 호출하고, 그 호출이 내부
gRPC 백엔드(Greeter.SayHello)로 전달되는지 end-to-end 로 확인한다.
"""

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import INVALID_NAME


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_hello_success(grpc_server):
    with TestClient(app) as client:
        resp = client.post("/hello", json={"name": "World"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "Hello, World!"
    assert "elapsed_ms" in body


def test_validation_rejects_empty_name():
    # 게이트웨이가 백엔드 호출 전에 Pydantic 으로 차단한다.
    with TestClient(app) as client:
        resp = client.post("/hello", json={"name": ""})
    assert resp.status_code == 422


def test_backend_invalid_argument_maps_to_400(grpc_server):
    # 검증은 통과(비어있지 않음)하지만 백엔드가 INVALID_ARGUMENT 로 abort 하면
    # 게이트웨이가 400 으로 매핑한다.
    with TestClient(app) as client:
        resp = client.post("/hello", json={"name": INVALID_NAME})
    assert resp.status_code == 400
