# Django protobuf 직렬화 데모 (1_bookstore)

이 예제의 `book.proto` 에는 **gRPC 서비스가 없습니다.** `Book`, `Customer`,
`Order(Customer, repeated Book)` 메시지만 정의되어 있습니다. 즉 주제는 gRPC
통신이 아니라 **protobuf 를 웹 서비스의 데이터 포맷으로 쓰는 것** —
직렬화(`SerializeToString`)와 역직렬화(`ParseFromString`) 그 자체입니다.

gRPC 서버/포트는 필요 없습니다.

## 구조

```
django/
├── manage.py
├── config/            # settings, urls, wsgi
├── gateway/           # app: views, urls, serializer, proto/
├── tests/             # 통합 테스트 (순수 HTTP)
└── docs/index.html    # 실무 적용 가이드 문서
```

## 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 헬스 체크 |
| POST | `/books` | JSON Book -> protobuf 직렬화 (크기/base64/왕복 일치) |
| POST | `/orders` | 중첩+repeated 가 포함된 Order 직렬화 |
| POST | `/books/decode` | base64 -> bytes -> Book 역직렬화 |

## 설치 & 실행

```bash
uv sync

# 앱 기동
uv run python manage.py runserver

# 호출 예
curl -X POST localhost:8000/books -H "content-type: application/json" \
  -d '{"isbn":"978-0134685991","title":"Effective Python","price":39.99}'
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 gRPC 서버 없이 순수 HTTP 로 직렬화 왕복/검증을 확인합니다.
자세한 설명은 `docs/index.html` 참고.
