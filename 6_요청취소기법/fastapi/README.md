# FastAPI HTTP→gRPC 게이트웨이 (6_요청취소기법)

이 예제의 gRPC 서버를 백엔드로 두고, FastAPI 가 REST 엔드포인트를 노출하는
게이트웨이(BFF) 샘플입니다. 핵심 주제는 **요청 취소**입니다.

- 호출마다 **per-call 데드라인(timeout)** 을 적용합니다. 초과 시 gRPC 가
  `DEADLINE_EXCEEDED` 를 던지고 서버 측 작업이 취소됩니다 → 게이트웨이는 **HTTP 504**.
- 클라이언트(브라우저)가 연결을 끊으면 `request.is_disconnected()` 로 감지하고
  `future.cancel()` 로 백엔드 호출을 취소해 **자원 낭비를 막습니다.**

## 구조

```
fastapi/
├── app/
│   ├── proto/         # 컴파일된 gRPC 코드
│   ├── grpc_client.py # 채널/스텁 + future 기반 호출/취소
│   ├── schemas.py     # Pydantic 요청/응답
│   ├── config.py      # 설정(환경변수)
│   └── main.py        # FastAPI 앱
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 기동 (상위 폴더의 예제 서버, 포트 50056)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run uvicorn app.main:app --reload

# 3) 호출 (충분한 데드라인)
curl -X POST localhost:8000/operation -H "content-type: application/json" \
     -d '{"data":"hello","deadline_ms":3000}'

# 4) 짧은 데드라인 → 504
curl -i -X POST localhost:8000/operation -H "content-type: application/json" \
     -d '{"data":"hello","deadline_ms":200}'
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 gRPC 서버를 직접 띄워 데드라인 초과(504)와 취소 가능 작업을
end-to-end 로 검증합니다. 자세한 설명은 `docs/index.html` 참고.
