"""게이트웨이 통합 테스트.

브라우저 대신 TestClient 로 REST 엔드포인트를 호출하고, 그 호출이 내부
gRPC 백엔드로 전달되며 **클라이언트 인터셉터**가 동작하는지 end-to-end 로
확인한다.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_echo_success(echo_server):
    with TestClient(app) as client:
        resp = client.post("/echo", json={"message": "Hello"})
    assert resp.status_code == 200
    body = resp.json()
    # test 서비서가 받은 메시지를 그대로 echo
    assert body["message"] == "Hello"
    assert "elapsed_ms" in body


def test_interceptor_injects_request_id(echo_server):
    """인터셉터 동작 증명 (1): x-request-id 자동 주입이 서버까지 전달됨."""
    with TestClient(app) as client:
        resp = client.post("/echo", json={"message": "Trace"})
    assert resp.status_code == 200
    body = resp.json()
    request_id = body["request_id"]
    # 인터셉터가 자동 주입한 request_id 가 응답에 실려 돌아온다(비어있지 않음).
    assert request_id
    # 서버가 실제로 그 x-request-id 를 수신했음을 확인(메타데이터 전파 증명).
    assert echo_server.received_request_ids[-1] == request_id


def test_interceptor_increments_call_count(echo_server):
    """인터셉터 동작 증명 (2): 가로챈 호출마다 call_count 가 증가한다."""
    with TestClient(app) as client:
        before = app.state.grpc.interceptor.call_count
        client.post("/echo", json={"message": "one"})
        client.post("/echo", json={"message": "two"})
        after = app.state.grpc.interceptor.call_count
    # 두 번 호출했으니 인터셉터도 두 번 실행되었어야 한다.
    assert after - before == 2


def test_validation_rejects_empty_message():
    with TestClient(app) as client:
        resp = client.post("/echo", json={"message": ""})
    assert resp.status_code == 422  # Pydantic 검증 실패
