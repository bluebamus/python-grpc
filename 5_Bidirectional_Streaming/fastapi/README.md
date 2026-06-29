# FastAPI HTTP→gRPC 게이트웨이 (5_Bidirectional_Streaming)

이 예제의 gRPC `ChatService`(양방향 스트리밍)를 백엔드로 두고, FastAPI 가
**WebSocket** 엔드포인트를 노출하는 게이트웨이(BFF) 샘플입니다. 클라이언트가
WebSocket 으로 보낸 메시지를 gRPC 양방향 스트림으로 중계하고, 서버 응답을 다시
WebSocket 으로 돌려줍니다.

## 구조

```
fastapi/
├── app/
│   ├── proto/         # 컴파일된 gRPC 코드 (messages_pb2*, ChatService)
│   ├── grpc_client.py # 채널/스텁 + 양방향 chat() 래퍼
│   ├── schemas.py     # 경계 모델 (health 등)
│   ├── config.py      # 설정(환경변수, 기본 target localhost:50055)
│   └── main.py        # FastAPI 앱 (WebSocket /ws/chat, GET /health)
├── tests/             # 통합 테스트 (echo 양방향 서버 직접 기동)
└── docs/index.html    # 실무 적용 가이드 문서
```

## 핵심 아이디어

비동기 WebSocket 과 동기 gRPC 양방향 스트림을 잇기 위해:

- **요청 제너레이터를 큐로 구동**: WebSocket 으로 도착한 텍스트를 큐에 넣고,
  제너레이터가 큐에서 꺼내 `ChatMessage` 로 yield → gRPC 요청 스트림이 된다.
- 블로킹 gRPC 호출은 **백그라운드 스레드**에서 돌리고, 응답을 다른 큐로 흘려
  이벤트 루프가 `run_in_executor` 로 소비한다.
- reader/writer 를 `asyncio.gather` 로 동시 구동해 진짜 양방향으로 동작한다.

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 (상위 폴더 예제, 포트 50055 로 맞춰 기동)
#    ※ 상위 server.py 는 50051 사용 → 게이트웨이 기본값과 맞추려면 GATEWAY_GRPC_TARGET 조정

# 2) 게이트웨이 기동
uv run uvicorn app.main:app --reload

# 3) WebSocket 접속 (예: websocat)
#    ws://localhost:8000/ws/chat 로 메시지를 보내면 echo 응답을 받는다.
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 echo 양방향 gRPC 서버(포트 50055)를 직접 띄워, WebSocket 으로 3개를
보내면 3개의 에코를 받는지 end-to-end 로 검증합니다. 자세한 설명은 `docs/index.html` 참고.
