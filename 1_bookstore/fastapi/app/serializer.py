"""protobuf 직렬화/역직렬화 핵심 모듈.

이 예제(1_bookstore)의 주제는 gRPC 통신이 아니라 **protobuf 그 자체를 데이터
포맷으로 쓰는 것**이다. 즉 Pydantic 으로 받은 JSON 입력을 protobuf 메시지로
바꾸고(`build_*`), 바이너리로 직렬화(`SerializeToString`)하며, 그 바이너리를
다시 메시지로 되돌린다(`ParseFromString`). 이 모듈이 그 변환을 전담한다.
"""

import base64

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import book_pb2

from app.schemas import BookIn, OrderIn


# --- Pydantic -> protobuf 메시지 ---------------------------------------------


def build_book(data: BookIn) -> "book_pb2.Book":
    """BookIn(Pydantic) -> book_pb2.Book(protobuf)."""
    return book_pb2.Book(
        isbn=data.isbn,
        title=data.title,
        author=data.author,
        publisher=data.publisher,
        published_date=data.published_date,
        price=data.price,
        page_count=data.page_count,
        genre=data.genre,
    )


def build_order(data: OrderIn) -> "book_pb2.Order":
    """OrderIn(Pydantic) -> book_pb2.Order.

    중첩 메시지(Customer)와 repeated 필드(items)를 함께 채우는 예시다.
    repeated 필드는 메시지 리스트를 그대로 넘기면 protobuf 가 복사해 담는다.
    """
    customer = book_pb2.Customer(
        id=data.customer.id,
        name=data.customer.name,
        email=data.customer.email,
        address=data.customer.address,
        phone_number=data.customer.phone_number,
    )
    return book_pb2.Order(
        order_number=data.order_number,
        customer=customer,
        items=[build_book(item) for item in data.items],
        order_date=data.order_date,
        shipping_status=data.shipping_status,
    )


# --- protobuf 메시지 -> dict (역직렬화 결과 노출용) --------------------------


def book_to_dict(book: "book_pb2.Book") -> dict:
    """book_pb2.Book -> JSON 직렬화 가능한 dict."""
    return {
        "isbn": book.isbn,
        "title": book.title,
        "author": book.author,
        "publisher": book.publisher,
        "published_date": book.published_date,
        # protobuf float(32bit) 는 미세 오차가 있을 수 있어 표시용으로 반올림한다.
        "price": round(book.price, 2),
        "page_count": book.page_count,
        "genre": book.genre,
    }


# --- 직렬화 / 역직렬화 핵심 -------------------------------------------------


def serialize(message) -> bytes:
    """protobuf 메시지를 바이너리 bytes 로 직렬화한다."""
    return message.SerializeToString()


def to_base64(data: bytes) -> str:
    """bytes 를 HTTP/JSON 으로 안전하게 실어 나르기 위해 base64 로 인코딩한다."""
    return base64.b64encode(data).decode("ascii")


def from_base64(data_base64: str) -> bytes:
    """base64 문자열을 다시 bytes 로 디코딩한다."""
    return base64.b64decode(data_base64)


def parse_book(data: bytes) -> "book_pb2.Book":
    """bytes -> book_pb2.Book 역직렬화."""
    book = book_pb2.Book()
    book.ParseFromString(data)
    return book


def roundtrip_book(book: "book_pb2.Book") -> bool:
    """직렬화한 뒤 다시 역직렬화한 메시지가 원본과 동일한지 확인한다.

    protobuf 메시지는 `==` 로 필드 단위 비교를 지원하므로, 왕복이 손실 없이
    이뤄졌음을 한 줄로 증명할 수 있다.
    """
    restored = parse_book(serialize(book))
    return restored == book
