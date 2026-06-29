# Django HTTP→gRPC 게이트웨이 (13_타임아웃설정과통신연결유지기법)

이 예제의 gRPC 서버를 백엔드로 두고, Django 가 REST 엔드포인트를 노출하는
게이트웨이 샘플입니다. 핵심은 두 가지입니다.

- **per-call deadline(timeout)**: 요청마다 데드라인을 적용해 호출하고, 백엔드가
  그 안에 응답하지 못하면 `DEADLINE_EXCEEDED` → **HTTP 504** 로 매핑합니다.
- **keepalive**: 장수명 gRPC 채널에 keepalive 옵션을 주입해 유휴 연결을 살립니다.

## 구조

```
django/
├── manage.py
├── config/            # settings(타임아웃·keepalive), urls, wsgi
├── gateway/           # app: views, urls, grpc_client, proto/
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 기동 (상위 폴더 예제 서버, 포트 50063 으로)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run python manage.py runserver

# 3) 호출 (deadline_ms 는 선택)
curl -X POST localhost:8000/echo -H "content-type: application/json" \
  -d '{"message":"Hello","deadline_ms":1000}'
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 서버가 일부러 2초 sleep 하도록 만들고 200ms 데드라인으로 호출해,
`DEADLINE_EXCEEDED` 가 504 로 매핑되는지 검증합니다.
