# FastAPI HTTP→gRPC 게이트웨이 (3_ServerStreaming)

이 예제의 gRPC 서버 스트리밍(요청 1개 → 응답 여러 개)을 백엔드로 두고,
FastAPI 가 REST 엔드포인트를 노출하는 게이트웨이(BFF) 샘플입니다.
핵심은 **서버 스트리밍을 HTTP 스트리밍(SSE)으로 중계**해, 백엔드가 보내는
메시지를 모아서 한 번에 주지 않고 도착하는 대로 클라이언트에 흘려보내는 것입니다.

## 구조

```
fastapi/
├── app/
│   ├── proto/         # 컴파일된 gRPC 코드 (ChatService)
│   ├── grpc_client.py # 채널/스텁 + 서버 스트림 순회(제너레이터)
│   ├── schemas.py     # Pydantic 요청 모델
│   ├── config.py      # 설정(환경변수, 기본 포트 50053)
│   └── main.py        # FastAPI 앱 (StreamingResponse, SSE)
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 기동 (상위 폴더의 예제 서버, 포트 50053)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run uvicorn app.main:app --reload

# 3) 호출 (SSE 스트림 수신)
curl -N -X POST localhost:8000/chat-stream \
  -H "content-type: application/json" -d '{"message":"시작"}'
```

`-N`(no-buffer)을 주면 메시지가 도착하는 대로 한 줄씩 출력됩니다:

```
data: {"index": 0, "message": "..."}

data: {"index": 1, "message": "..."}

event: done
data: {"count": 3}
```

## 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 헬스 체크 (200) |
| POST | `/chat-stream` | `{"message":"..."}` → SSE(`text/event-stream`) 스트림 |

## 테스트

```bash
uv run pytest
```

통합 테스트는 gRPC 서버를 직접 띄워 N개의 메시지가 SSE 로 끝까지 전달되는지,
백엔드 부재 시 503 매핑되는지 end-to-end 로 검증합니다.
자세한 설명은 `docs/index.html` 참고.
