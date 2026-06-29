"""REST 요청/응답 스키마 (Pydantic).

protobuf 메시지(`book_pb2.Book` 등)를 HTTP 경계에서 그대로 노출하지 않고,
Pydantic 모델을 따로 둔다. 이렇게 하면 (1) 입력 검증(필수 필드 누락 시 422)을
선언적으로 처리하고, (2) 내부 proto 스키마 변경이 외부 API 계약으로 곧바로
새는 것을 막을 수 있다. proto <-> Pydantic 변환은 serializer.py 가 담당한다.
"""

from pydantic import BaseModel, Field


class BookIn(BaseModel):
    """입력용 책 모델. isbn/title 은 필수(누락 시 422)."""

    isbn: str = Field(..., min_length=1, examples=["978-0134685991"])
    title: str = Field(..., min_length=1, examples=["Effective Python"])
    author: str = Field("", examples=["Brett Slatkin"])
    publisher: str = Field("", examples=["Addison-Wesley"])
    published_date: str = Field("", examples=["2019-11-15"])
    price: float = Field(0.0, examples=[39.99])
    page_count: int = Field(0, examples=[480])
    genre: str = Field("", examples=["Programming"])


class CustomerIn(BaseModel):
    """입력용 고객 모델. id/name 은 필수."""

    id: str = Field(..., min_length=1, examples=["cust-001"])
    name: str = Field(..., min_length=1, examples=["홍길동"])
    email: str = Field("", examples=["hong@example.com"])
    address: str = Field("", examples=["서울시 강남구"])
    phone_number: str = Field("", examples=["010-1234-5678"])


class OrderIn(BaseModel):
    """입력용 주문 모델. 중첩(customer)과 repeated(items)를 포함한다."""

    order_number: str = Field(..., min_length=1, examples=["ORD-20260524-001"])
    customer: CustomerIn
    items: list[BookIn] = Field(..., min_length=1)
    order_date: str = Field("", examples=["2026-05-24"])
    shipping_status: str = Field("", examples=["PREPARING"])


class DecodeRequest(BaseModel):
    """base64 로 인코딩된 직렬화 bytes 를 받아 Book 으로 되돌리는 요청."""

    data_base64: str = Field(..., min_length=1)


class SerializeResponse(BaseModel):
    """직렬화 결과 응답.

    - book/order: 왕복(직렬화→역직렬화)으로 복원한 필드(원본 일치 증명용)
    - serialized_size: 직렬화된 bytes 길이
    - serialized_base64: bytes 를 base64 로 인코딩한 문자열(전송/저장용)
    - roundtrip_ok: ParseFromString 으로 되돌린 메시지가 원본과 동일한지
    """

    serialized_size: int
    serialized_base64: str
    roundtrip_ok: bool
