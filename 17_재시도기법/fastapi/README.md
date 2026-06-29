# FastAPI HTTP→gRPC 게이트웨이 (17_재시도기법)

이 예제의 gRPC 서버를 백엔드로 두고, FastAPI 가 REST 엔드포인트를 노출하는
게이트웨이(BFF) 샘플입니다. 핵심은 **gRPC 채널의 재시도 정책**을 게이트웨이
계층에 적용해, 백엔드의 일시적 실패(UNAVAILABLE)를 자동으로 흡수하는 것입니다.

## 구조

```
fastapi/
├── app/
│   ├── proto/         # 컴파일된 gRPC 코드
│   ├── grpc_client.py # 채널/스텁 + 재시도 service_config
│   ├── schemas.py     # Pydantic 요청/응답
│   ├── config.py      # 설정(환경변수)
│   └── main.py        # FastAPI 앱
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 기동 (상위 폴더의 예제 서버)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run uvicorn app.main:app --reload

# 3) 호출
curl -X POST localhost:8000/unary -H "content-type: application/json" -d '{"message":"Hello"}'
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 gRPC 서버를 직접 띄워 재시도/에러매핑을 end-to-end 로 검증합니다.
자세한 설명은 `docs/index.html` 참고.
