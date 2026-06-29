# FastAPI HTTP→gRPC 게이트웨이 (9_인터셉터)

이 예제의 gRPC 서버(`EchoService`)를 백엔드로 두고, FastAPI 가 REST 엔드포인트를
노출하는 게이트웨이(BFF) 샘플입니다. 핵심은 **gRPC 클라이언트 인터셉터**
(`grpc.UnaryUnaryClientInterceptor`)를 직접 구현해 채널에 적용하는 것입니다.
인터셉터는 (1) 호출 시작/종료 로깅, (2) `x-request-id` 메타데이터 자동 주입을
담당합니다.

## 구조

```
fastapi/
├── app/
│   ├── proto/         # 컴파일된 gRPC 코드
│   ├── grpc_client.py # 채널/스텁 + 클라이언트 인터셉터
│   ├── schemas.py     # Pydantic 요청/응답
│   ├── config.py      # 설정(환경변수)
│   └── main.py        # FastAPI 앱
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 기동 (상위 폴더의 예제 서버, 포트 50059)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run uvicorn app.main:app --reload

# 3) 호출
curl -X POST localhost:8000/echo -H "content-type: application/json" -d '{"message":"Hello"}'
```

응답 예: `{"message":"Hello","request_id":"<자동주입된 id>","elapsed_ms":1.23}`

## 테스트

```bash
uv run pytest
```

통합 테스트는 gRPC 서버를 직접 띄워, 인터셉터가 주입한 `x-request-id` 가 서버까지
전달되는지와 인터셉터의 `call_count` 가 증가하는지를 end-to-end 로 검증합니다.
자세한 설명은 `docs/index.html` 참고.
