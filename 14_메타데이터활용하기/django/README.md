# Django HTTP→gRPC 게이트웨이 (14_메타데이터활용하기)

이 예제의 gRPC 서버를 백엔드로 두고, Django 가 REST 엔드포인트를 노출하는
게이트웨이 샘플입니다. 핵심은 **HTTP 헤더를 gRPC 메타데이터로 변환/주입**하고,
서버가 돌려준 메타데이터를 다시 HTTP 응답으로 노출하는 것입니다.

- `Authorization`, `X-Request-Id` 헤더 → gRPC 메타데이터(`authorization`, `x-request-id`)
- `X-Request-Id` 가 없으면 게이트웨이가 생성(분산 추적 상관키)
- 서버는 수신 메타데이터를 trailing metadata 로 되돌리고, 게이트웨이는 이를
  응답 바디(`request_id`)와 헤더(`X-Request-Id`, `X-Auth-Present`)로 노출

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

# 1) 백엔드 gRPC 서버 기동 (포트 50064 로 띄워야 합니다)

# 2) 게이트웨이 기동
uv run python manage.py runserver

# 3) 호출 (헤더로 메타데이터 전달)
curl -X POST localhost:8000/echo \
  -H "content-type: application/json" \
  -H "X-Request-Id: req-123" \
  -H "Authorization: Bearer token" \
  -d '{"message":"Hello"}'
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 gRPC 서버(포트 50064)를 직접 띄워 **메타데이터 왕복**을
end-to-end 로 검증합니다.
