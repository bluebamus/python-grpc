"""게이트웨이 통합 테스트.

브라우저 대신 TestClient 로 REST 엔드포인트를 호출하고, 그 호출이 내부
gRPC 백엔드로 전달되는지 end-to-end 로 확인한다. 특히 /services 가 서버
리플렉션을 통해 EchoService 를 동적으로 발견하는지 검증한다.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_echo_success(grpc_server):
    with TestClient(app) as client:
        resp = client.post("/echo", json={"message": "Hello"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Hello"


def test_services_lists_echo_service(grpc_server):
    # 리플렉션으로 서버가 노출하는 서비스 목록을 받아온다.
    with TestClient(app) as client:
        resp = client.get("/services")
    assert resp.status_code == 200
    services = resp.json()["services"]
    # 리플렉션으로 EchoService 가 발견되었다는 증거
    assert "reflection_example.EchoService" in services


def test_validation_rejects_empty_message():
    with TestClient(app) as client:
        resp = client.post("/echo", json={"message": ""})
    assert resp.status_code == 422  # Pydantic 검증 실패
