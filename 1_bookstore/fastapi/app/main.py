"""FastAPI 앱 — protobuf 를 웹 서비스의 데이터 포맷으로 쓰는 데모.

이 예제(1_bookstore)의 book.proto 에는 gRPC 서비스가 없고 message 만 있다.
따라서 gRPC 서버/포트는 필요 없다. 대신 REST 로 JSON 을 받아 protobuf 메시지로
변환해 직렬화(SerializeToString)하고, 그 바이너리를 다시 역직렬화
(ParseFromString)하는 왕복을 보여준다.
"""

from fastapi import FastAPI

from app.config import settings
from app.schemas import (
    BookIn,
    DecodeRequest,
    OrderIn,
    SerializeResponse,
)
from app import serializer

app = FastAPI(title=settings.app_title)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/books")
def serialize_book(req: BookIn) -> dict:
    """JSON Book -> protobuf 직렬화. 크기/base64 와 왕복 일치 여부를 반환한다."""
    book = serializer.build_book(req)
    data = serializer.serialize(book)
    payload = SerializeResponse(
        serialized_size=len(data),
        serialized_base64=serializer.to_base64(data),
        roundtrip_ok=serializer.roundtrip_book(book),
    )
    # 응답에 원본 book(왕복 복원본)도 함께 실어, 직렬화 전후가 같음을 보인다.
    return {"book": serializer.book_to_dict(serializer.parse_book(data)), **payload.model_dump()}


@app.post("/orders")
def serialize_order(req: OrderIn) -> dict:
    """JSON Order -> protobuf 직렬화.

    중첩(customer)과 repeated(items) 가 포함된 메시지가 하나의 바이너리로
    직렬화되는 것을 보여준다. items 개수가 늘면 serialized_size 도 커진다.
    """
    order = serializer.build_order(req)
    data = serializer.serialize(order)
    return {
        "order_number": order.order_number,
        "item_count": len(order.items),
        "serialized_size": len(data),
        "serialized_base64": serializer.to_base64(data),
    }


@app.post("/books/decode")
def decode_book(req: DecodeRequest) -> dict:
    """base64(직렬화된 Book bytes) -> 역직렬화 -> JSON.

    /books 가 돌려준 serialized_base64 를 그대로 넣으면 원본 필드가 복원된다.
    """
    data = serializer.from_base64(req.data_base64)
    book = serializer.parse_book(data)
    return {"book": serializer.book_to_dict(book)}
