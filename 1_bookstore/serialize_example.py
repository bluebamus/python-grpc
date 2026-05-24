"""
온라인 서점 protobuf 직렬화/역직렬화 실습

실행 전 준비:
    uv run python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. book.proto

실행:
    uv run python serialize_example.py
"""

import book_pb2


def main():
    # 1) 책 객체 생성 및 데이터 설정
    book = book_pb2.Book()
    book.isbn = "978-0134685991"
    book.title = "Effective Python"
    book.author = "Brett Slatkin"
    book.publisher = "Addison-Wesley"
    book.published_date = "2019-11-15"
    book.price = 39.99
    book.page_count = 480
    book.genre = "Programming"

    print("=== 원본 객체 ===")
    print(book)

    # 2) 직렬화 (Serialization) — 바이너리 bytes
    serialized_book = book.SerializeToString()
    print("=== 직렬화 결과 (bytes) ===")
    print(serialized_book)
    print(f"크기: {len(serialized_book)} bytes\n")

    # 3) 역직렬화 (Deserialization)
    deserialized_book = book_pb2.Book()
    deserialized_book.ParseFromString(serialized_book)

    print("=== 역직렬화 결과 ===")
    print(deserialized_book)

    # 4) 고객 + 주문 예시 (중첩 메시지 / repeated)
    customer = book_pb2.Customer(
        id="cust-001",
        name="홍길동",
        email="hong@example.com",
        address="서울시 강남구",
        phone_number="010-1234-5678",
    )

    order = book_pb2.Order(
        order_number="ORD-20260524-001",
        customer=customer,
        items=[book],
        order_date="2026-05-24",
        shipping_status="PREPARING",
    )

    print("=== 주문 객체 ===")
    print(order)

    order_bytes = order.SerializeToString()
    print(f"주문 직렬화 크기: {len(order_bytes)} bytes")


if __name__ == "__main__":
    main()
