"""Django 게이트웨이 통합 테스트."""

from django.test import Client

client = Client()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_echo_success(grpc_server_factory):
    # 서버가 즉시 응답하므로 짧은 데드라인이어도 성공한다.
    grpc_server_factory(sleep_s=0)
    resp = client.post(
        "/echo",
        data={"message": "Hello", "deadline_ms": 1000},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Received: Hello"


def test_echo_uses_default_deadline(grpc_server_factory):
    # deadline_ms 생략 → 설정 기본값(1000ms) → 즉시 응답 성공.
    grpc_server_factory(sleep_s=0)
    resp = client.post(
        "/echo", data={"message": "Default"}, content_type="application/json"
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Received: Default"


def test_echo_deadline_exceeded_returns_504(grpc_server_factory):
    # 서버가 2초 sleep, 데드라인 200ms → DEADLINE_EXCEEDED → 504
    grpc_server_factory(sleep_s=2.0)
    resp = client.post(
        "/echo",
        data={"message": "Slow", "deadline_ms": 200},
        content_type="application/json",
    )
    assert resp.status_code == 504


def test_validation_rejects_empty_message():
    resp = client.post(
        "/echo", data={"message": ""}, content_type="application/json"
    )
    assert resp.status_code == 422
