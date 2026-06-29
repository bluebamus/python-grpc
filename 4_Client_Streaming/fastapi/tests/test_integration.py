"""게이트웨이 통합 테스트.

브라우저 대신 TestClient 로 REST 엔드포인트를 호출하고, 그 호출이 내부
gRPC 백엔드로 **요청 스트림**으로 전달되어 단일 응답으로 집계되는지를
end-to-end 로 확인한다.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_stream_data_aggregates(grpc_server):
    # 리스트를 보내면 게이트웨이가 요청 스트림으로 변환 -> 서버가 집계 -> 단일 result
    with TestClient(app) as client:
        resp = client.post("/stream-data", json={"items": ["a", "b", "c"]})
    assert resp.status_code == 200
    body = resp.json()
    # 서버가 받은 요청들을 모아 개수/연결 문자열로 집계했는지 확인
    assert body["result"] == "count=3;data=a|b|c"
    assert body["count"] == 3
    assert "elapsed_ms" in body


def test_stream_data_single_item(grpc_server):
    with TestClient(app) as client:
        resp = client.post("/stream-data", json={"items": ["solo"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"] == "count=1;data=solo"
    assert body["count"] == 1


def test_validation_rejects_empty_items():
    with TestClient(app) as client:
        resp = client.post("/stream-data", json={"items": []})
    assert resp.status_code == 422  # 빈 items 는 Pydantic 검증 실패


def test_validation_rejects_missing_items():
    with TestClient(app) as client:
        resp = client.post("/stream-data", json={})
    assert resp.status_code == 422
