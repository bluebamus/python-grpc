"""Django 게이트웨이 통합 테스트."""

import base64

from django.test import Client

from tests.conftest import KNOWN_ID, PAYLOAD_SIZE

client = Client()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_get_data_compressed_success(grpc_server):
    # 압축 채널로 큰 반복 bytes 를 받아 정상 디코딩되는지 확인
    resp = client.get(f"/data/{KNOWN_ID}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_id"] == KNOWN_ID
    assert body["size"] == PAYLOAD_SIZE
    decoded = base64.b64decode(body["data_base64"])
    assert decoded == b"X" * PAYLOAD_SIZE
    assert "elapsed_ms" in body


def test_get_data_not_found_maps_to_404(grpc_server):
    resp = client.get("/data/does-not-exist")
    assert resp.status_code == 404
