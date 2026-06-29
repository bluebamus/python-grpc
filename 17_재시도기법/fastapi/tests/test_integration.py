"""게이트웨이 통합 테스트.

브라우저 대신 TestClient 로 REST 엔드포인트를 호출하고, 그 호출이 내부
gRPC 백엔드로 전달되며 재시도 정책이 동작하는지 end-to-end 로 확인한다.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_unary_success_without_failures(grpc_server_factory):
    servicer = grpc_server_factory(fail_times=0)
    with TestClient(app) as client:
        resp = client.post("/unary", json={"message": "Hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "Received: Hello"
    assert servicer.calls == 1  # 실패가 없으니 재시도도 없다


def test_unary_retries_then_succeeds(grpc_server_factory):
    # 처음 2번 UNAVAILABLE -> 채널이 자동 재시도 -> 3번째에 성공
    servicer = grpc_server_factory(fail_times=2)
    with TestClient(app) as client:
        resp = client.post("/unary", json={"message": "Retry"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Received: Retry"
    assert servicer.calls == 3  # 2 실패 + 1 성공 = 재시도가 일어났다는 증거


def test_unary_exhausts_retries_returns_503(grpc_server_factory):
    # maxAttempts=5 보다 많이 실패시키면 재시도를 모두 소진하고 503 으로 매핑된다
    servicer = grpc_server_factory(fail_times=100)
    with TestClient(app) as client:
        resp = client.post("/unary", json={"message": "Nope"})
    assert resp.status_code == 503
    assert servicer.calls == 5  # maxAttempts 만큼만 시도


def test_validation_rejects_empty_message():
    with TestClient(app) as client:
        resp = client.post("/unary", json={"message": ""})
    assert resp.status_code == 422  # Pydantic 검증 실패
