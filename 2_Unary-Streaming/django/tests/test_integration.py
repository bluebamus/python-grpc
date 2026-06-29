"""Django 게이트웨이 통합 테스트."""

from django.test import Client

from tests.conftest import INVALID_NAME

client = Client()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_hello_success(grpc_server):
    resp = client.post("/hello", data={"name": "World"}, content_type="application/json")
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "Hello, World!"
    assert "elapsed_ms" in body


def test_validation_rejects_empty_name():
    resp = client.post("/hello", data={"name": ""}, content_type="application/json")
    assert resp.status_code == 422


def test_backend_invalid_argument_maps_to_400(grpc_server):
    # 검증은 통과(비어있지 않음)하지만 백엔드가 INVALID_ARGUMENT 로 abort 하면
    # 게이트웨이가 400 으로 매핑한다.
    resp = client.post("/hello", data={"name": INVALID_NAME}, content_type="application/json")
    assert resp.status_code == 400
