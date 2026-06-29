# gRPC 예제별 실무 샘플 프로젝트 (FastAPI / Django) 설계

날짜: 2026-06-29

## 목표

코드가 있는 각 예제 폴더에 대해, 그 예제를 실무에 적용하는 샘플 프로젝트를
FastAPI 기반과 Django 기반으로 각각 만든다. 각 샘플은 uv 기반 `pyproject.toml`로
독립 실행/테스트되며, 실무 적용 방식·호출 흐름·고려사항을 정리한 HTML 문서를 포함한다.

## 범위

- **대상 폴더(코드 있음, 17개)**: `1_bookstore`, `2_Unary-Streaming`, `3_ServerStreaming`,
  `4_Client_Streaming`, `5_Bidirectional_Streaming`, `6_요청취소기법`, `7_데이터압축하기`,
  `8_데이터압축기법`, `9_인터셉터`, `10_에러핸들링`, `11_서버상태체크-healthcheck`,
  `12_서버의정보받아오기-리플렉션`, `13_타임아웃설정과통신연결유지기법`, `14_메타데이터활용하기`,
  `16_TLS보안`, `17_재시도기법`, `19_asyncio와threading`
- **제외 폴더(코드 없음)**: `15_gRPC의보안개요`, `18_실시간채팅을위한비동기개념`,
  `20_마이크로서비스아키텍쳐와gRPC`
- **진행 방식**: 파일럿 1개(`17_재시도기법`)로 FastAPI/Django 템플릿을 완성·검증한 뒤,
  승인되면 나머지 16개에 동일 패턴으로 확장한다.

## 핵심 결정 (사용자 승인됨)

1. 구조: 각 예제 폴더 **하위에** `fastapi/`, `django/` 서브폴더를 만든다. 기존 예제 코드는 유지.
2. 통합 패턴: **HTTP → gRPC 게이트웨이(BFF)**. 웹 앱이 REST를 노출하고 내부에서 해당
   예제의 gRPC 서버를 클라이언트로 호출한다.
3. 테스트: **통합 테스트 중심**. pytest fixture로 gRPC 서버를 띄우고 HTTP 엔드포인트를 E2E 검증.
4. 패키징: 각 샘플은 **독립 uv `pyproject.toml`** (루트와 분리), `requires-python = ">=3.13"`.

## 디렉터리 구조 (예: 17_재시도기법)

```
17_재시도기법/
├── server.py / client.py / example.proto / *_pb2*.py   ← 기존 (유지)
├── fastapi/
│   ├── pyproject.toml          # uv, [tool.pytest.ini_options] 포함
│   ├── README.md
│   ├── app/
│   │   ├── proto/              # 해당 .proto 복사 + 컴파일된 *_pb2*.py
│   │   ├── grpc_client.py      # 채널/스텁 (+ 예제 핵심 옵션: 재시도 service_config)
│   │   ├── schemas.py          # Pydantic 모델
│   │   ├── config.py           # 설정(gRPC 타깃 주소 등)
│   │   └── main.py             # FastAPI 앱 + 엔드포인트
│   ├── tests/test_integration.py
│   └── docs/index.html
└── django/
    ├── pyproject.toml
    ├── README.md
    ├── manage.py
    ├── config/                 # settings.py, urls.py, wsgi/asgi
    ├── gateway/                # app: views.py, urls.py, grpc_client.py, proto/
    ├── tests/test_integration.py
    └── docs/index.html
```

## 통합 패턴 상세

- REST 엔드포인트(예: `POST /unary`, body `{"message": "..."}`)를 노출.
- 내부에서 gRPC 서버(`localhost:50051`)를 클라이언트로 호출.
- 각 예제의 핵심 기능을 게이트웨이 계층에서 실무적으로 적용:
  - 17(재시도): `grpc.service_config` 채널 옵션으로 재시도 정책 적용.
  - 10(에러핸들링)·기타: gRPC StatusCode → HTTP 상태코드 매핑.
  - 스트리밍 예제(3/4/5): SSE 또는 청크 응답 등 적절한 HTTP 매핑.
- gRPC 에러 코드 → HTTP 매핑 규칙: UNAVAILABLE→503, DEADLINE_EXCEEDED→504,
  INVALID_ARGUMENT→400, NOT_FOUND→404, 그 외→500.

## 테스트 전략 (통합 중심)

- pytest fixture가 해당 예제 `server.py`의 서비서를 백그라운드 스레드로 50051에 기동.
- FastAPI: `httpx` + ASGI transport(또는 `TestClient`)로 엔드포인트 호출.
- Django: `pytest-django` + test client로 view 호출.
- 예제별 핵심 동작 검증(예: 17은 다회 호출 시 재시도로 정상 응답 수렴).
- 실행: `uv run pytest`.

## 의존성 (pyproject.toml)

- FastAPI: `fastapi`, `uvicorn`, `grpcio`, `grpcio-tools`, `pydantic`, `pydantic-settings`;
  dev: `pytest`, `httpx`.
- Django: `django`, `grpcio`, `grpcio-tools`; dev: `pytest`, `pytest-django`.

## HTML 문서 (docs/index.html)

각 샘플 폴더마다 단일 HTML(인라인 CSS). 섹션:
1. 개요 — 이 예제를 실무 어디에 쓰는가
2. 아키텍처/흐름도 — 브라우저 → REST → 게이트웨이 → gRPC 서버
3. 호출 흐름 — 요청/응답 단계별 시퀀스
4. 코드 핵심 포인트 — 예제별 핵심 옵션/로직
5. 실무 적용 시 고려사항 — 멱등성, 백오프/지터, 타임아웃 조합, 관측성, 보안 등
6. 실행·테스트 — `uv sync`, `uv run`, `uv run pytest`

## 검증 기준

- 파일럿(`17_재시도기법`)의 FastAPI/Django 샘플이 각각 `uv run pytest`로 통과.
- 각 샘플에 동작하는 `docs/index.html` 존재.
- 기존 예제 코드 변경 없음(하위 폴더 추가만).
```
