# Django HTTP→gRPC 게이트웨이 (5_Bidirectional_Streaming)

이 예제의 gRPC `ChatService`(양방향 스트리밍)를 백엔드로 두는 Django 게이트웨이
샘플입니다. 양방향 스트리밍은 본래 WebSocket/지속 연결이 필요하지만,
**Django(WSGI)는 진정한 양방향/WebSocket 에 부적합**합니다. 따라서 실무적 대안으로
**반이중 배치** 엔드포인트를 제공합니다.

> Django 에서 진짜 양방향이 필요하면 **Channels/ASGI** 로 전환해야 합니다.
> 자세한 한계는 `docs/index.html` 5절 참고.

## 엔드포인트

- `GET /health` → `{"status":"ok"}`
- `POST /chat-batch` body `{"messages":[...]}` → `{"replies":[...]}`
  (messages 를 bidi 스트림으로 보내고 응답들을 모아 반환)

## 구조

```
django/
├── config/   # settings(GRPC_TARGET=localhost:50055), urls, wsgi
├── gateway/  # views, urls, grpc_client(chat_batch), proto/
├── tests/    # echo 양방향 서버 직접 기동 + 통합 테스트
└── docs/index.html
```

## 설치 & 실행

```bash
uv sync

# 백엔드 gRPC 서버 (양방향 ChatService, 포트 50055)
uv run python manage.py runserver

# 호출
curl -X POST localhost:8000/chat-batch \
  -H "content-type: application/json" \
  -d '{"messages":["a","b","c"]}'
# -> {"replies":["echo: a","echo: b","echo: c"]}
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 echo 양방향 gRPC 서버(포트 50055)를 직접 띄워, 보낸 메시지 개수와
동일한 개수의 replies 를 받는지 검증합니다.
