"""Django 게이트웨이 통합 테스트."""

from django.test import Client

client = Client()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_divide_success():
    resp = client.post(
        "/divide", data={"dividend": 10, "divisor": 2}, content_type="application/json"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["quotient"] == 5.0
    assert "elapsed_ms" in body


def test_divide_by_zero_maps_to_400():
    # divisor=0 -> 서버가 INVALID_ARGUMENT abort -> 뷰가 HTTP 400
    resp = client.post(
        "/divide", data={"dividend": 10, "divisor": 0}, content_type="application/json"
    )
    assert resp.status_code == 400
    error = resp.json()["error"]
    assert error["grpc_status"] == "INVALID_ARGUMENT"
    assert error["http_status"] == 400
    assert "zero" in error["detail"].lower()


def test_permission_denied_maps_to_403():
    # dividend<0 -> 서버가 PERMISSION_DENIED abort -> 뷰가 HTTP 403
    resp = client.post(
        "/divide", data={"dividend": -4, "divisor": 2}, content_type="application/json"
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["grpc_status"] == "PERMISSION_DENIED"


def test_validation_rejects_non_numeric():
    # 숫자가 아닌 입력은 gRPC 호출 전 422 로 막힌다
    resp = client.post(
        "/divide", data={"dividend": "abc", "divisor": 2}, content_type="application/json"
    )
    assert resp.status_code == 422
