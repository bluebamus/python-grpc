"""Django 게이트웨이 통합 테스트."""

from django.test import Client

client = Client()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_operation_succeeds_with_enough_deadline(grpc_server):
    # 작업은 약 1초. 데드라인을 충분히(3초) 주면 끝까지 수행되어 200.
    resp = client.post(
        "/operation",
        data={"data": "hello", "deadline_ms": 3000},
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"] == "completed: hello"
    assert body["elapsed_ms"] > 0


def test_operation_short_deadline_returns_504(grpc_server):
    # 데드라인이 너무 짧으면(200ms < 1초) DEADLINE_EXCEEDED → 504. 서버 작업도 취소된다.
    resp = client.post(
        "/operation",
        data={"data": "hello", "deadline_ms": 200},
        content_type="application/json",
    )
    assert resp.status_code == 504
    # 서버 측이 취소를 감지해 일찍 종료했는지 확인(취소 가능 작업 시연).
    assert grpc_server.last_cancelled.wait(timeout=2.0)


def test_validation_rejects_empty_data():
    resp = client.post(
        "/operation",
        data={"data": ""},
        content_type="application/json",
    )
    assert resp.status_code == 422
