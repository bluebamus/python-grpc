"""게이트웨이 통합 테스트.

브라우저 대신 TestClient 로 REST 엔드포인트를 호출하고, 그 호출이 내부
gRPC 백엔드로 전달되며 에러가 올바른 HTTP 상태코드로 매핑되는지
end-to-end 로 확인한다.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_divide_success():
    with TestClient(app) as client:
        resp = client.post("/divide", json={"dividend": 10, "divisor": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["quotient"] == 5.0
    assert "elapsed_ms" in body


def test_divide_by_zero_maps_to_400():
    # divisor=0 -> 서버가 INVALID_ARGUMENT abort -> 게이트웨이가 HTTP 400
    with TestClient(app) as client:
        resp = client.post("/divide", json={"dividend": 10, "divisor": 0})
    assert resp.status_code == 400
    error = resp.json()["error"]
    assert error["grpc_status"] == "INVALID_ARGUMENT"
    assert error["http_status"] == 400
    assert "zero" in error["detail"].lower()


def test_permission_denied_maps_to_403():
    # dividend<0 -> 서버가 PERMISSION_DENIED abort -> 게이트웨이가 HTTP 403
    # (gRPC StatusCode -> HTTP 매핑 표가 동작함을 보이는 추가 검증)
    with TestClient(app) as client:
        resp = client.post("/divide", json={"dividend": -4, "divisor": 2})
    assert resp.status_code == 403
    error = resp.json()["error"]
    assert error["grpc_status"] == "PERMISSION_DENIED"


def test_validation_rejects_non_numeric():
    # 숫자가 아닌 입력은 Pydantic 검증에서 422 로 막힌다 (gRPC 호출 전 차단)
    with TestClient(app) as client:
        resp = client.post("/divide", json={"dividend": "abc", "divisor": 2})
    assert resp.status_code == 422
