# gRPC 샘플 브라우저 E2E (Playwright)

샘플 게이트웨이의 **스트리밍 동작을 실제 브라우저(Chromium)** 로 검증하는 E2E 하니스입니다.
httpx 기반 통합 테스트가 다루지 못하는 "진짜 브라우저 런타임" 경로(EventSource·WebSocket)를
검증합니다.

## 무엇을 검증하나

- **서버 스트리밍 → SSE** (3_ServerStreaming 계열): 브라우저 `EventSource` 가 게이트웨이
  `/sse` 를 구독 → gRPC 서버 스트리밍 응답 4개가 DOM 에 렌더링되는지 확인.
- **양방향 → WebSocket** (5_Bidirectional 계열): 브라우저 `WebSocket` 이 `/ws` 로 a/b/c 전송
  → gRPC 양방향 echo 3개(`echo: a/b/c`)가 DOM 에 렌더링되는지 확인.
- 게이트웨이 자체 헬스(`/health`).

## 구조

```
e2e_playwright/
├── app/
│   ├── proto/           # chat.proto(ServerStream+BiDi) 컴파일 산출물
│   ├── grpc_server.py   # 결정론적 ChatService 서버
│   └── main.py          # FastAPI: HTML 클라이언트 + /sse(SSE) + /ws(WebSocket)
├── tests/
│   ├── conftest.py      # gRPC 서버 + uvicorn 게이트웨이 백그라운드 기동
│   └── test_browser_streaming.py
└── pyproject.toml
```

self-contained 하니스로, 게이트웨이가 클라이언트 HTML 을 **동일 출처**로 서빙하므로
CORS 설정 없이 EventSource/WebSocket 이 동작합니다.

## 실행

```bash
uv sync
uv run playwright install chromium   # 최초 1회: 헤드리스 Chromium 다운로드(~110MB)
uv run pytest
```

> 다른 샘플들의 통합 테스트는 브라우저 없이 `run_all_sample_tests.sh` 로 실행합니다.
> 이 E2E 는 브라우저 다운로드가 필요해 별도로 둡니다.
