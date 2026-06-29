"""게이트웨이 통합 테스트.

브라우저 대신 TestClient 로 REST 엔드포인트를 호출하고, 그 호출이 내부
gRPC 백엔드로 전달되며 per-call deadline 이 동작하는지 end-to-end 로 확인한다.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_echo_success(grpc_server_factory):
    # 서버가 즉시 응답하므로 짧은 데드라인이어도 성공한다.
    grpc_server_factory(sleep_s=0)
    with TestClient(app) as client:
        resp = client.post("/echo", json={"message": "Hello", "deadline_ms": 1000})
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "Received: Hello"
    assert body["elapsed_ms"] >= 0


def test_echo_uses_default_deadline(grpc_server_factory):
    # deadline_ms 를 주지 않으면 설정 기본값(1000ms)으로 호출 → 즉시 응답 성공.
    grpc_server_factory(sleep_s=0)
    with TestClient(app) as client:
        resp = client.post("/echo", json={"message": "Default"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Received: Default"


def test_echo_deadline_exceeded_returns_504(grpc_server_factory):
    # 서버가 2초 sleep 하는데 데드라인은 200ms → DEADLINE_EXCEEDED → 504
    grpc_server_factory(sleep_s=2.0)
    with TestClient(app) as client:
        resp = client.post("/echo", json={"message": "Slow", "deadline_ms": 200})
    assert resp.status_code == 504


def test_validation_rejects_empty_message():
    with TestClient(app) as client:
        resp = client.post("/echo", json={"message": ""})
    assert resp.status_code == 422  # Pydantic 검증 실패
