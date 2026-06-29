"""게이트웨이 통합 테스트.

브라우저 대신 TestClient 로 REST 엔드포인트를 호출하고, 그 호출이 내부
gRPC 백엔드로 gzip 압축 채널을 통해 전달되며 정상 디코딩되는지 end-to-end
로 확인한다.
"""

import base64

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import KNOWN_ID, PAYLOAD_SIZE


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_get_data_compressed_success(grpc_server):
    # 압축 채널로 큰 반복 bytes 를 받아 정상 디코딩되는지 확인
    with TestClient(app) as client:
        resp = client.get(f"/data/{KNOWN_ID}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_id"] == KNOWN_ID
    assert body["size"] == PAYLOAD_SIZE
    # base64 를 되돌리면 원본 페이로드와 정확히 일치해야 한다
    decoded = base64.b64decode(body["data_base64"])
    assert decoded == b"X" * PAYLOAD_SIZE
    assert "elapsed_ms" in body


def test_get_data_not_found_maps_to_404(grpc_server):
    with TestClient(app) as client:
        resp = client.get("/data/does-not-exist")
    assert resp.status_code == 404
