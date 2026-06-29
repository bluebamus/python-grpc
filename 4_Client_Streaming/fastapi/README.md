# FastAPI HTTP→gRPC 게이트웨이 (4_Client_Streaming)

이 예제의 gRPC 서버를 백엔드로 두고, FastAPI 가 REST 엔드포인트를 노출하는
게이트웨이(BFF) 샘플입니다. 핵심은 **클라이언트 스트리밍**입니다. REST 로 받은
`items` 리스트를 gRPC **요청 스트림**으로 변환해 `StreamData` 를 호출하고,
서버가 집계한 **단일 응답**을 다시 HTTP 응답으로 돌려줍니다.

## 구조

```
fastapi/
├── app/
│   ├── proto/         # 컴파일된 gRPC 코드 (streaming.proto)
│   ├── grpc_client.py # 채널/스텁 + 요청 스트림 제너레이터
│   ├── schemas.py     # Pydantic 요청/응답
│   ├── config.py      # 설정(환경변수, 기본 포트 50054)
│   └── main.py        # FastAPI 앱
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 기동 (상위 폴더의 예제 서버, 포트 50054 로 띄울 것)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run uvicorn app.main:app --reload

# 3) 호출
curl -X POST localhost:8000/stream-data \
  -H "content-type: application/json" \
  -d '{"items":["a","b","c"]}'
```

응답 예시:

```json
{"result": "...", "count": 3, "elapsed_ms": 1.23}
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 gRPC 서버를 직접 띄워, 게이트웨이가 리스트를 요청 스트림으로
보내고 서버가 집계한 결과를 받는 흐름을 end-to-end 로 검증합니다.
자세한 설명은 `docs/index.html` 참고.
