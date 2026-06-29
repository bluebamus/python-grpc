"""Django 게이트웨이 통합 테스트.

REST 호출이 내부 gRPC 백엔드로 전달되며 **클라이언트 인터셉터**가 동작하는지
end-to-end 로 확인한다.
"""

from django.test import Client

from gateway.grpc_client import get_client

client = Client()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_echo_success(echo_server):
    resp = client.post("/echo", data={"message": "Hello"}, content_type="application/json")
    assert resp.status_code == 200
    body = resp.json()
    # test 서비서가 받은 메시지를 그대로 echo
    assert body["message"] == "Hello"
    assert "elapsed_ms" in body


def test_interceptor_injects_request_id(echo_server):
    """인터셉터 동작 증명 (1): x-request-id 자동 주입이 서버까지 전달됨."""
    resp = client.post("/echo", data={"message": "Trace"}, content_type="application/json")
    assert resp.status_code == 200
    request_id = resp.json()["request_id"]
    # 인터셉터가 자동 주입한 request_id 가 응답에 실려 돌아온다(비어있지 않음).
    assert request_id
    # 서버가 실제로 그 x-request-id 를 수신했음을 확인(메타데이터 전파 증명).
    assert echo_server.received_request_ids[-1] == request_id


def test_interceptor_increments_call_count(echo_server):
    """인터셉터 동작 증명 (2): 가로챈 호출마다 call_count 가 증가한다."""
    before = get_client().interceptor.call_count
    client.post("/echo", data={"message": "one"}, content_type="application/json")
    client.post("/echo", data={"message": "two"}, content_type="application/json")
    after = get_client().interceptor.call_count
    assert after - before == 2


def test_validation_rejects_empty_message():
    resp = client.post("/echo", data={"message": ""}, content_type="application/json")
    assert resp.status_code == 422
