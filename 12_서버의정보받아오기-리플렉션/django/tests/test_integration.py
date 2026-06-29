"""Django 게이트웨이 통합 테스트.

REST 엔드포인트 호출이 내부 gRPC 백엔드로 전달되는지 확인한다. 특히
/services 가 서버 리플렉션으로 EchoService 를 동적으로 발견하는지 검증한다.
"""

from django.test import Client

client = Client()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_echo_success(grpc_server):
    resp = client.post("/echo", data={"message": "Hello"}, content_type="application/json")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Hello"


def test_services_lists_echo_service(grpc_server):
    # 리플렉션으로 서버가 노출하는 서비스 목록을 받아온다.
    resp = client.get("/services")
    assert resp.status_code == 200
    services = resp.json()["services"]
    # 리플렉션으로 EchoService 가 발견되었다는 증거
    assert "reflection_example.EchoService" in services


def test_validation_rejects_empty_message():
    resp = client.post("/echo", data={"message": ""}, content_type="application/json")
    assert resp.status_code == 422
