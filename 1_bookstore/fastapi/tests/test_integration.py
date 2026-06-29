"""통합 테스트 (순수 HTTP).

이 예제는 gRPC 서버가 없으므로 외부 프로세스를 띄울 필요가 없다. TestClient
로 REST 엔드포인트를 호출해, protobuf 직렬화/역직렬화 왕복이 HTTP 경계에서
올바로 동작하는지 검증한다.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_books_serialize_roundtrip():
    resp = client.post(
        "/books",
        json={
            "isbn": "978-0134685991",
            "title": "Effective Python",
            "author": "Brett Slatkin",
            "price": 39.99,
            "page_count": 480,
            "genre": "Programming",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["roundtrip_ok"] is True
    assert body["serialized_size"] > 0
    assert body["serialized_base64"]
    # 왕복 복원된 book 의 필드가 원본과 일치
    assert body["book"]["isbn"] == "978-0134685991"
    assert body["book"]["title"] == "Effective Python"


def test_orders_with_repeated_items():
    # repeated items 가 2개면, 1개일 때보다 직렬화 크기가 커야 한다.
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
    r1 = client.post("/orders", json=one_item)
    r2 = client.post("/orders", json=two_items)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["item_count"] == 1
    assert r2.json()["item_count"] == 2
    # repeated 가 직렬화에 반영된다는 증거
    assert r2.json()["serialized_size"] > r1.json()["serialized_size"]


def test_decode_restores_original_fields():
    # 1) /books 로 직렬화 base64 를 얻고
    serialized = client.post(
        "/books",
        json={"isbn": "978-1", "title": "Decoded Title", "author": "Some Author"},
    ).json()
    b64 = serialized["serialized_base64"]

    # 2) /books/decode 에 넣으면 원본 필드가 복원된다
    decoded = client.post("/books/decode", json={"data_base64": b64})
    assert decoded.status_code == 200
    book = decoded.json()["book"]
    assert book["isbn"] == "978-1"
    assert book["title"] == "Decoded Title"
    assert book["author"] == "Some Author"


def test_validation_missing_required_field():
    # title 누락 -> Pydantic 검증 실패(422)
    resp = client.post("/books", json={"isbn": "978-1"})
    assert resp.status_code == 422


def test_orders_validation_requires_items():
    # items 가 빈 리스트면 422 (min_length=1)
    resp = client.post(
        "/orders",
        json={
            "order_number": "ORD-1",
            "customer": {"id": "c1", "name": "n"},
            "items": [],
        },
    )
    assert resp.status_code == 422
