# FastAPI HTTP→gRPC 게이트웨이 (11_서버상태체크-healthcheck)

이 예제의 gRPC 헬스체크 서버를 백엔드로 두고, FastAPI 가 REST 엔드포인트를
노출하는 게이트웨이(BFF) 샘플입니다. 핵심은 **표준 gRPC 헬스체크 프로토콜**
(`grpc.health.v1.health/Check`)을 호출해 백엔드 서비스의 서빙 상태를 HTTP 로
변환하는 것입니다. 쿠버네티스 등의 probe 를 REST 로 노출할 때 쓰는 패턴입니다.

## 엔드포인트

| 메서드/경로 | 의미 |
|---|---|
| `GET /health` | 게이트웨이 자체 헬스 (항상 200) |
| `GET /health/grpc?service=<name>` | 백엔드 gRPC `Check` 호출 → 상태를 HTTP 로 매핑 |

상태 매핑: `SERVING → 200`, `NOT_SERVING/SERVICE_UNKNOWN/UNKNOWN → 503`.

## 구조

```
fastapi/
├── app/
│   ├── proto/         # 컴파일된 gRPC 코드 (health_check_*)
│   ├── grpc_client.py # 채널/스텁 + Check 호출
│   ├── schemas.py     # Pydantic 응답
│   ├── config.py      # 설정(환경변수, 기본 target=localhost:50061)
│   └── main.py        # FastAPI 앱 + 상태/에러 매핑
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 헬스체크 서버 기동 (상위 폴더의 예제 서버, 포트 50061)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run uvicorn app.main:app --reload

# 3) 호출
curl localhost:8000/health
curl localhost:8000/health/grpc?service=api
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 결정론적 헬스체크 서버(서비스명→상태 매핑)를 직접 띄워
SERVING→200, NOT_SERVING→503, 알 수 없는 서비스→503 매핑을 end-to-end 로
검증합니다. 자세한 설명은 `docs/index.html` 참고.
