# Django HTTP→gRPC 게이트웨이 (3_ServerStreaming)

이 예제의 gRPC 서버 스트리밍(요청 1개 → 응답 여러 개)을 백엔드로 두고,
Django 가 REST 엔드포인트를 노출하는 게이트웨이 샘플입니다.
핵심은 **서버 스트리밍을 `StreamingHttpResponse` 로 중계**해, 백엔드가 보내는
메시지를 도착하는 대로 SSE(`text/event-stream`) 청크로 흘려보내는 것입니다.

## 구조

```
django/
├── manage.py
├── config/            # settings(포트 50053), urls, wsgi
├── gateway/           # app: views(StreamingHttpResponse), urls, grpc_client, proto/
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 기동 (상위 폴더 예제 서버, 포트 50053)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run python manage.py runserver

# 3) 호출 (SSE 스트림 수신)
curl -N -X POST localhost:8000/chat-stream \
  -H "content-type: application/json" -d '{"message":"시작"}'
```

## 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 헬스 체크 (200) |
| POST | `/chat-stream` | `{"message":"..."}` → SSE 스트림 |

## 테스트

```bash
uv run pytest
```

통합 테스트는 gRPC 서버를 직접 띄워 N개의 메시지가 `streaming_content` 로
끝까지 전달되는지, 백엔드 부재 시 503 매핑되는지 검증합니다.
