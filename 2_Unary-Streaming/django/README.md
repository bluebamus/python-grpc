# Django HTTP→gRPC 게이트웨이 (2_Unary-Streaming)

이 예제의 gRPC 서버(`Greeter` 서비스)를 백엔드로 두고, Django 가 REST
엔드포인트를 노출하는 게이트웨이 샘플입니다. 가장 기본적인 **Unary RPC**
(`SayHello`)를 HTTP 경계로 감쌉니다.

## 구조

```
django/
├── manage.py
├── config/            # settings, urls, wsgi
├── gateway/           # app: views, urls, grpc_client, proto/
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 기동 (상위 폴더 예제 서버, 포트 50052)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run python manage.py runserver

# 3) 호출
curl -X POST localhost:8000/hello -H "content-type: application/json" -d '{"name":"World"}'
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 결정론적 `Greeter` 서버를 직접 띄워 `/health` 200, 정상 `SayHello`
성공, 빈 `name` → 422, 백엔드 INVALID_ARGUMENT → 400 을 검증합니다.
