"""protobuf 직렬화/역직렬화 핵심 모듈 (Django).

FastAPI 샘플의 app/serializer.py 와 동일한 원리다. 이 예제(1_bookstore)에는
gRPC 서비스가 없고 message 만 있으므로, 주제는 **protobuf 를 데이터 포맷으로
쓰는 것** — 직렬화(SerializeToString)/역직렬화(ParseFromString) 그 자체다.

Django 에는 Pydantic 이 없으므로, 입력 dict 검증은 views.py 가 담당하고
여기서는 dict <-> protobuf 변환과 직렬화만 다룬다.
"""

import base64

from gateway import proto  # noqa: F401  (sys.path 등록)
import book_pb2


# --- dict -> protobuf 메시지 -------------------------------------------------


def build_book(data: dict) -> "book_pb2.Book":
    """입력 dict -> book_pb2.Book. 누락 필드는 protobuf 기본값으로 채워진다."""
    return book_pb2.Book(
        isbn=data.get("isbn", ""),
        title=data.get("title", ""),
        author=data.get("author", ""),
        publisher=data.get("publisher", ""),
        published_date=data.get("published_date", ""),
        price=float(data.get("price", 0.0) or 0.0),
        page_count=int(data.get("page_count", 0) or 0),
        genre=data.get("genre", ""),
    )


def build_order(data: dict) -> "book_pb2.Order":
    """입력 dict -> book_pb2.Order.

    중첩 메시지(Customer)와 repeated 필드(items)를 함께 채우는 예시다.
    """
    customer_data = data.get("customer", {})
    customer = book_pb2.Customer(
        id=customer_data.get("id", ""),
        name=customer_data.get("name", ""),
        email=customer_data.get("email", ""),
        address=customer_data.get("address", ""),
        phone_number=customer_data.get("phone_number", ""),
    )
    return book_pb2.Order(
        order_number=data.get("order_number", ""),
        customer=customer,
        items=[build_book(item) for item in data.get("items", [])],
        order_date=data.get("order_date", ""),
        shipping_status=data.get("shipping_status", ""),
    )


# --- protobuf 메시지 -> dict ------------------------------------------------


def book_to_dict(book: "book_pb2.Book") -> dict:
    return {
        "isbn": book.isbn,
        "title": book.title,
        "author": book.author,
        "publisher": book.publisher,
        "published_date": book.published_date,
        # protobuf float(32bit) 미세 오차를 표시용으로 반올림한다.
        "price": round(book.price, 2),
        "page_count": book.page_count,
        "genre": book.genre,
    }


# --- 직렬화 / 역직렬화 핵심 -------------------------------------------------


def serialize(message) -> bytes:
    return message.SerializeToString()


def to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def from_base64(data_base64: str) -> bytes:
    return base64.b64decode(data_base64)


def parse_book(data: bytes) -> "book_pb2.Book":
    book = book_pb2.Book()
    book.ParseFromString(data)
    return book


def roundtrip_book(book: "book_pb2.Book") -> bool:
    """직렬화→역직렬화 왕복이 원본과 동일한지(손실 없는지) 확인한다."""
    restored = parse_book(serialize(book))
    return restored == book
