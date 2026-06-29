"""Django 게이트웨이 통합 테스트."""

from django.test import Client

client = Client()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_stream_data_aggregates(grpc_server):
    # 리스트를 보내면 게이트웨이가 요청 스트림으로 변환 -> 서버가 집계 -> 단일 result
    resp = client.post(
        "/stream-data",
        data={"items": ["a", "b", "c"]},
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"] == "count=3;data=a|b|c"
    assert body["count"] == 3
    assert "elapsed_ms" in body


def test_stream_data_single_item(grpc_server):
    resp = client.post(
        "/stream-data",
        data={"items": ["solo"]},
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"] == "count=1;data=solo"
    assert body["count"] == 1


def test_validation_rejects_empty_items():
    resp = client.post(
        "/stream-data",
        data={"items": []},
        content_type="application/json",
    )
    assert resp.status_code == 422


def test_validation_rejects_missing_items():
    resp = client.post(
        "/stream-data",
        data={},
        content_type="application/json",
    )
    assert resp.status_code == 422
