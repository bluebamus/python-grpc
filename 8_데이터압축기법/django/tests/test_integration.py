"""Django 게이트웨이 통합 테스트."""

import base64

from django.test import Client

from tests.conftest import make_payload

client = Client()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_get_data_gzip(grpc_server):
    resp = client.get("/data/1", {"compression": "gzip"})
    assert resp.status_code == 200
    body = resp.json()
    expected = make_payload("1")
    assert body["data_id"] == "1"
    assert body["compression"] == "gzip"
    assert body["size"] == len(expected)
    assert base64.b64decode(body["data_base64"]) == expected


def test_get_data_none(grpc_server):
    resp = client.get("/data/1", {"compression": "none"})
    assert resp.status_code == 200
    body = resp.json()
    expected = make_payload("1")
    assert body["compression"] == "none"
    assert body["size"] == len(expected)
    assert base64.b64decode(body["data_base64"]) == expected


def test_gzip_and_none_same_size(grpc_server):
    gzip_resp = client.get("/data/42", {"compression": "gzip"})
    none_resp = client.get("/data/42", {"compression": "none"})
    assert gzip_resp.status_code == 200
    assert none_resp.status_code == 200
    assert gzip_resp.json()["size"] == none_resp.json()["size"]
    assert gzip_resp.json()["data_base64"] == none_resp.json()["data_base64"]


def test_get_data_deflate(grpc_server):
    resp = client.get("/data/7", {"compression": "deflate"})
    assert resp.status_code == 200
    body = resp.json()
    expected = make_payload("7")
    assert body["compression"] == "deflate"
    assert body["size"] == len(expected)
    assert base64.b64decode(body["data_base64"]) == expected


def test_get_data_default_compression(grpc_server):
    # compression 미지정 시 채널 기본 압축(settings: gzip)이 적용된다.
    resp = client.get("/data/9")
    assert resp.status_code == 200
    body = resp.json()
    assert body["compression"] == "gzip"
    assert body["size"] == len(make_payload("9"))


def test_invalid_compression_returns_400(grpc_server):
    resp = client.get("/data/1", {"compression": "brotli"})
    assert resp.status_code == 400
