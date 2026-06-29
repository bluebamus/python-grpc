"""게이트웨이 통합 테스트.

브라우저 대신 TestClient 로 REST 엔드포인트를 호출하고, 그 호출이 내부 gRPC
백엔드로 전달되며 per-call 데드라인과 취소 매핑이 동작하는지 end-to-end 로 확인한다.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_operation_succeeds_with_enough_deadline(grpc_server):
    # 작업은 약 1초 걸린다. 데드라인을 충분히(3초) 주면 끝까지 수행되어 200.
    with TestClient(app) as client:
        resp = client.post("/operation", json={"data": "hello", "deadline_ms": 3000})
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"] == "completed: hello"
    assert body["elapsed_ms"] > 0


def test_operation_short_deadline_returns_504(grpc_server):
    # 데드라인이 너무 짧으면(200ms < 1초) gRPC 가 DEADLINE_EXCEEDED 를 던지고,
    # 게이트웨이는 이를 HTTP 504 로 매핑한다. 서버 작업도 취소되어 일찍 종료된다.
    with TestClient(app) as client:
        resp = client.post("/operation", json={"data": "hello", "deadline_ms": 200})
    assert resp.status_code == 504
    # 서버 측이 취소를 감지해 일찍 종료했는지 확인(취소 가능 작업 시연).
    assert grpc_server.last_cancelled.wait(timeout=2.0)


def test_validation_rejects_empty_data():
    with TestClient(app) as client:
        resp = client.post("/operation", json={"data": ""})
    assert resp.status_code == 422  # Pydantic 검증 실패
