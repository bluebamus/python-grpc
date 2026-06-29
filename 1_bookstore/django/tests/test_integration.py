"""Django 통합 테스트 (순수 HTTP).

gRPC 서버가 없으므로 외부 프로세스가 필요 없다. Django 테스트 클라이언트로
REST 엔드포인트를 호출해 protobuf 직렬화/역직렬화 왕복을 검증한다.
"""

import json

from django.test import Client

client = Client()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_books_serialize_roundtrip():
    resp = client.post(
        "/books",
        data={
            "isbn": "978-0134685991",
            "title": "Effective Python",
            "author": "Brett Slatkin",
            "price": 39.99,
            "page_count": 480,
            "genre": "Programming",
        },
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["roundtrip_ok"] is True
    assert body["serialized_size"] > 0
    assert body["serialized_base64"]
    assert body["book"]["isbn"] == "978-0134685991"
    assert body["book"]["title"] == "Effective Python"


def test_orders_with_repeated_items():
    one_item = {
        "order_number": "ORD-1",
        "customer": {"id": "cust-001", "name": "홍길동"},
        "items": [{"isbn": "isbn-1", "title": "Book One"}],
    }
    two_items = {
        "order_number": "ORD-2",
        "customer": {"id": "cust-001", "name": "홍길동"},
        "items": [
            {"isbn": "isbn-1", "title": "Book One"},
            {"isbn": "isbn-2", "title": "Book Two"},
        ],
    }
    r1 = client.post("/orders", data=one_item, content_type="application/json")
    r2 = client.post("/orders", data=two_items, content_type="application/json")
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["item_count"] == 1
    assert r2.json()["item_count"] == 2
    assert r2.json()["serialized_size"] > r1.json()["serialized_size"]


def test_decode_restores_original_fields():
    serialized = client.post(
        "/books",
        data={"isbn": "978-1", "title": "Decoded Title", "author": "Some Author"},
        content_type="application/json",
    ).json()
    b64 = serialized["serialized_base64"]

    decoded = client.post(
        "/books/decode",
        data={"data_base64": b64},
        content_type="application/json",
    )
    assert decoded.status_code == 200
    book = decoded.json()["book"]
    assert book["isbn"] == "978-1"
    assert book["title"] == "Decoded Title"
    assert book["author"] == "Some Author"


def test_validation_missing_required_field():
    # title 누락 -> 422
    resp = client.post(
        "/books",
        data={"isbn": "978-1"},
        content_type="application/json",
    )
    assert resp.status_code == 422


def test_orders_validation_requires_items():
    resp = client.post(
        "/orders",
        data={
            "order_number": "ORD-1",
            "customer": {"id": "c1", "name": "n"},
            "items": [],
        },
        content_type="application/json",
    )
    assert resp.status_code == 422
