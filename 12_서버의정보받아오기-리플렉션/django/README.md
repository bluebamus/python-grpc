# Django HTTP→gRPC 게이트웨이 (12_서버의정보받아오기-리플렉션)

이 예제의 gRPC 서버를 백엔드로 두고, Django 가 REST 엔드포인트를 노출하는
게이트웨이 샘플입니다. 핵심은 **gRPC 서버 리플렉션**으로, 클라이언트가 .proto
파일을 미리 갖고 있지 않아도 서버에 직접 물어 어떤 서비스를 노출하는지 동적으로
발견합니다.

## 구조

```
django/
├── manage.py
├── config/            # settings, urls, wsgi
├── gateway/           # app: views, urls, grpc_client, proto/
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 헬스 체크 |
| POST | `/echo` | `{"message":"..."}` 를 Echo 로 호출 |
| GET | `/services` | 서버 리플렉션으로 서비스 목록 조회 |

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 기동 (상위 폴더 예제 서버, 포트 50062 로 수정 후)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run python manage.py runserver

# 3) 호출
curl localhost:8000/services
curl -X POST localhost:8000/echo -H "content-type: application/json" -d '{"message":"Hello"}'
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 리플렉션을 켠 gRPC 서버를 직접 띄워, `/services` 가
`reflection_example.EchoService` 를 발견하는지 검증합니다.
