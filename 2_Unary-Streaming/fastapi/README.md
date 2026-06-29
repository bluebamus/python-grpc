# FastAPI HTTP→gRPC 게이트웨이 (2_Unary-Streaming)

이 예제의 gRPC 서버(`Greeter` 서비스)를 백엔드로 두고, FastAPI 가 REST
엔드포인트를 노출하는 게이트웨이(BFF) 샘플입니다. 가장 기본적인 **Unary RPC**
(`SayHello`)를 HTTP 경계로 감싸 외부에는 표준 REST 로, 내부에는 gRPC 로 통신합니다.

## 구조

```
fastapi/
├── app/
│   ├── proto/         # 컴파일된 gRPC 코드 (helloworld_pb2*.py)
│   ├── grpc_client.py # 채널/스텁 + SayHello 호출
│   ├── schemas.py     # Pydantic 요청/응답
│   ├── config.py      # 설정(환경변수, 기본 target localhost:50052)
│   └── main.py        # FastAPI 앱 (POST /hello, GET /health)
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 기동 (상위 폴더의 예제 서버, 포트는 50052 로 맞춰 사용)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run uvicorn app.main:app --reload

# 3) 호출
curl -X POST localhost:8000/hello -H "content-type: application/json" -d '{"name":"World"}'
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 결정론적 `Greeter` 서버를 직접 띄워 성공 응답·입력 검증·에러 매핑을
end-to-end 로 검증합니다. 자세한 설명은 `docs/index.html` 참고.
