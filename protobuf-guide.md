# Protocol Buffers (protobuf) 학습 가이드

## 1. Protocol Buffers란?

**Protocol Buffers**는 Google이 만든 **데이터 직렬화 포맷**입니다. JSON이나 XML처럼 데이터를 표현하지만, **바이너리 형식**이라 더 작고 빠릅니다.

비교:

| 항목 | JSON | Protobuf |
|------|------|----------|
| 형식 | 텍스트 | 바이너리 |
| 크기 | 큼 | 작음 (3~10배 절약) |
| 속도 | 느림 | 빠름 |
| 사람이 읽기 | 쉬움 | 어려움 |
| 스키마 | 없음 (자유) | 필수 (`.proto` 파일) |

## 2. gRPC와 protobuf의 관계

gRPC는 **통신 프레임워크**, protobuf는 **데이터 포맷**입니다.

```
[Client] ── (protobuf 메시지) ──> [Server]
         HTTP/2 위에서 gRPC가 전송
```

gRPC가 두 가지를 protobuf로 정의합니다:
1. **서비스(Service)** — 어떤 함수(RPC)를 부를 수 있는가
2. **메시지(Message)** — 함수가 주고받는 데이터 구조

## 3. `.proto` 파일 기본 구조

```proto
syntax = "proto3";              // 버전 선언 (proto3 권장)

service MyService {             // 서비스 = 호출 가능한 함수들의 묶음
    rpc MyMethod (MyRequest) returns (MyResponse) {}
}

message MyRequest {             // 메시지 = 데이터 구조
    string message = 1;         // 필드 = 타입 이름 = 번호;
}

message MyResponse {
    string message = 1;
}
```

### 핵심 규칙

- **필드 번호(`= 1`)** 는 바이너리에서 필드를 식별하는 ID. 이름이 아니라 번호로 식별하므로 **한 번 정한 번호는 바꾸지 않는다**.
- **타입**: `string`, `int32`, `int64`, `bool`, `float`, `double`, `bytes`, 그리고 다른 메시지 타입.
- **rpc 문법**: `rpc 메서드명 (요청타입) returns (응답타입) {}`
- **repeated** 키워드: 배열/리스트를 표현. 예: `repeated string tags = 1;`

## 4. 중첩 메시지 (Nested Messages)

메시지 안에 메시지를 정의할 수 있습니다. 관련 데이터를 캡슐화하고 이름 충돌을 피할 때 사용합니다.

```proto
message Person {
    string name = 1;

    // 중첩 메시지 정의
    message Address {
        string street = 1;
        string city = 2;
        string zip = 3;
    }

    Address home = 2;          // 같은 메시지 안에서는 그대로 사용
    repeated Address others = 3;
}
```

### 외부에서 참조

```proto
message Company {
    Person.Address headquarters = 1;   // 바깥에서는 Person.Address로 접근
}
```

### Python에서 사용

```python
person = Person()
person.home.city = "Seoul"          // 중첩 메시지 필드 직접 접근
addr = Person.Address(city="Busan") // 클래스로도 접근 가능
```

## 5. 필드 옵션 (Options)

옵션은 필드 뒤에 **대괄호 `[...]`** 로 붙입니다.

### 형식

```proto
타입 필드명 = 번호 [옵션1 = 값1, 옵션2 = 값2];
```

### 주요 옵션

| 옵션 | 의미 | 예시 |
|------|------|------|
| `deprecated = true` | 더 이상 사용하지 말라는 표시 (코드 생성 시 경고) | `string old_name = 1 [deprecated = true];` |
| `packed = true` | `repeated` 원시타입을 효율적으로 인코딩 (proto3는 기본값) | `repeated int32 ids = 1 [packed = true];` |
| `default = 값` | 필드 기본값 (**proto2 전용**, proto3에서는 미지원) | `optional int32 age = 1 [default = 20];` |
| `(custom_option) = 값` | 사용자 정의 옵션 (괄호로 감쌈) | `string url = 1 [(my_validator.regex) = "^https?://"];` |

### 예시 모음

```proto
syntax = "proto3";

message User {
    string id = 1;
    string old_username = 2 [deprecated = true];          // 폐기 예정
    repeated int32 friend_ids = 3 [packed = true];        // 효율적 인코딩
    string email = 4 [(validate.rules).string.email = true];  // 커스텀 옵션
}
```

### proto2 vs proto3 기본값

- **proto2**: `[default = "anonymous"]`처럼 명시 가능
- **proto3**: 기본값 고정 — 숫자는 `0`, 문자열은 `""`, bool은 `false`. 사용자 정의 불가.

## 6. 컴파일 방법 (proto → Python)

```
my_service.proto
       │
       │  python -m grpc_tools.protoc ...
       ▼
my_service_pb2.py         ← 메시지 클래스
my_service_pb2_grpc.py    ← gRPC stub/servicer
```

### 명령어

```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. addressbook.proto
```

### 옵션 설명

| 옵션 | 의미 |
|------|------|
| `-m grpc_tools.protoc` | **Python의 `-m` 플래그**. 설치된 모듈(`grpc_tools.protoc`)을 스크립트로 실행 |
| `-I.` | **Include path**. `.proto` 파일을 찾을 디렉토리 (`.` = 현재 폴더). 여러 번 지정 가능 |
| `--python_out=.` | **메시지 클래스**(`_pb2.py`) 출력 디렉토리 |
| `--grpc_python_out=.` | **gRPC 서비스 코드**(`_pb2_grpc.py`) 출력 디렉토리 |
| `addressbook.proto` | 컴파일할 입력 `.proto` 파일명 (여러 개 나열 가능) |

### 주의

- `-I` 는 **대문자 i** 입니다. 소문자 `-i`는 다른 옵션이거나 인식되지 않습니다.
- 옵션 사이는 **공백**으로 구분. `-I.` 또는 `-I .` 둘 다 가능.
- 출력 디렉토리는 **미리 존재**해야 합니다.

## 7. 생성된 파일 사용

**서버 측:**
```python
import my_service_pb2
import my_service_pb2_grpc

class MyServiceServicer(my_service_pb2_grpc.MyServiceServicer):
    def MyMethod(self, request, context):
        return my_service_pb2.MyResponse(message=f"Hello {request.message}")
```

**클라이언트 측:**
```python
stub = my_service_pb2_grpc.MyServiceStub(channel)
response = stub.MyMethod(my_service_pb2.MyRequest(message="world"))
```

## 8. 왜 이런 구조를 쓰는가

- **언어 독립** — `.proto` 하나로 Python, Go, Java, C++ 등에서 모두 호환 코드 생성
- **계약(contract) 명시** — 서버/클라이언트가 같은 `.proto`를 공유하므로 인터페이스가 명확
- **버전 진화 안전** — 필드 번호 규칙 덕분에 기존 클라이언트를 깨지 않고 필드 추가 가능

## 한 줄 요약

> `.proto`로 **데이터 구조와 서비스를 정의**하고, **컴파일러가 Python 코드를 생성**하면, gRPC가 그것을 HTTP/2 위에서 빠르게 주고받게 해준다.

---

# 실습 과제 : 온라인 서점 데이터 모델링

## 요구사항 분석

온라인 서점에서 필요한 핵심 데이터는 다음과 같습니다.

1. **책 (book)**: isbn, 제목, 저자, 출판사, 출판일, 가격, 페이지 수, 장르
2. **저자 (author)**: 이름, 소개
3. **출판사 (publisher)**: 이름, 주소, 연락처
4. **고객 (customer)**: 아이디, 이름, 이메일, 주소, 연락처
5. **주문 (order)**: 주문번호, 고객 정보, 주문 상품 목록, 주문 날짜, 배송 상태

## 모델링 실습 1) protobuf 메시지 정의 (파일명은 `book.proto`)

```proto
syntax="proto3";

// 책 정보
message Book{
   string isbn=1;
   string title=2;
   string author=3;
   string publisher=4;
   string published_date=5;
   float price=6;
   int32 page_count=7;
   string genre=8;
}

// 고객정보
message Customer{
   string id=1;
   string name=2;
   string email=3;
   string address=4;
   string phone_number=5;
}

// 주문 정보
message Order{
   string order_number=1;
   Customer.customer=2;
   repeated Book.items=3;
   string order_date=4;
   string shipping_status=5;
}
```

## 모델링 실습 2) 컴파일

```bash
python -m grpc_tools.protoc -i=. --python_out=. --grpc_python_out=.book.proto
```

## 모델링 실습 3) 직렬화 / 역직렬화

```python
import book_pb2

# 책 객체 생성 및 데이터 설정
book = book_pb2.book()
book.isbn = "978-0134685991"
book.title = "Effective Python"

# ...

# 직렬화 (Setialization)
serialized_book = book.SerializeeToString()

print(setialized_book)

# 역직렬화 (Deserialization)
deserialized_book = book_pb2.Book()
deserialiized_book.ParseFromString(serialized_book)

print(deserialized_book)
```
