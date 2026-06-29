"""게이트웨이 통합 테스트.

브라우저 대신 TestClient 로 REST 엔드포인트를 호출하고, 그 호출이 내부
gRPC 백엔드로 전달되며 **HTTP 헤더 -> gRPC 메타데이터 -> HTTP 응답** 으로
왕복하는지 end-to-end 로 확인한다.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_echo_success(grpc_server):
    with TestClient(app) as client:
        resp = client.post("/echo", json={"message": "Hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "Echo: Hello"
    assert "request_id" in body
    assert isinstance(body["elapsed_ms"], (int, float))


def test_metadata_roundtrip_request_id(grpc_server):
    """클라이언트가 보낸 X-Request-Id 가 gRPC 메타데이터로 전달되고
    응답(바디/헤더)에 그대로 반영됨을 단언한다."""
    sent_id = "req-abc-123"
    with TestClient(app) as client:
        resp = client.post(
            "/echo",
            json={"message": "Trace me"},
            headers={"X-Request-Id": sent_id},
        )
    assert resp.status_code == 200
    body = resp.json()
    # 왕복 증명: 보낸 ID 가 응답 바디와 응답 헤더 양쪽에 동일하게 반영.
    assert body["request_id"] == sent_id
    assert resp.headers.get("X-Request-Id") == sent_id


def test_gateway_generates_request_id_when_missing(grpc_server):
    """X-Request-Id 를 보내지 않으면 게이트웨이가 생성해 채워준다."""
    with TestClient(app) as client:
        resp = client.post("/echo", json={"message": "No id"})
    assert resp.status_code == 200
    generated = resp.json()["request_id"]
    assert generated  # 비어있지 않음
    assert generated.startswith("gw-")
    assert resp.headers.get("X-Request-Id") == generated


def test_authorization_present(grpc_server):
    """Authorization 헤더가 있으면 서버가 메타데이터로 인지한다."""
    with TestClient(app) as client:
        resp = client.post(
            "/echo",
            json={"message": "With auth"},
            headers={"Authorization": "Bearer token-xyz"},
        )
    assert resp.status_code == 200
    assert resp.headers.get("X-Auth-Present") == "true"


def test_authorization_absent(grpc_server):
    """Authorization 헤더가 없으면 서버 메타데이터에도 없음으로 보인다."""
    with TestClient(app) as client:
        resp = client.post("/echo", json={"message": "No auth"})
    assert resp.status_code == 200
    assert resp.headers.get("X-Auth-Present") == "false"


def test_validation_rejects_empty_message():
    with TestClient(app) as client:
        resp = client.post("/echo", json={"message": ""})
    assert resp.status_code == 422  # Pydantic 검증 실패
