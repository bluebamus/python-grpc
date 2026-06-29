# FastAPI HTTP→gRPC 게이트웨이 (7_데이터압축하기)

이 예제의 gRPC 서버를 백엔드로 두고, FastAPI 가 REST 엔드포인트를 노출하는
게이트웨이(BFF) 샘플입니다. 핵심은 **gRPC 채널/호출에 gzip 압축**을 적용해,
큰 바이너리 응답(`bytes`)을 적은 네트워크 비용으로 주고받는 것입니다.

## 구조

```
fastapi/
├── app/
│   ├── proto/         # 컴파일된 gRPC 코드
│   ├── grpc_client.py # 압축(gzip) 채널/스텁
│   ├── schemas.py     # Pydantic 응답 (bytes -> base64)
│   ├── config.py      # 설정(환경변수)
│   └── main.py        # FastAPI 앱
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 기동 (상위 폴더의 예제 서버, 포트 50057 로 조정 필요)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run uvicorn app.main:app --reload

# 3) 호출 (data_id -> bytes 를 base64 로 받음)
curl localhost:8000/data/1
```

응답 예시:

```json
{"data_id":"1","data_base64":"WFhYWA...","size":10000,"elapsed_ms":3.1}
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 gRPC 서버를 직접 띄워, 압축 채널로 큰 반복 bytes 를 받아
정상 디코딩(size 확인)되는지와 NOT_FOUND→404 매핑을 end-to-end 로 검증합니다.
자세한 설명은 `docs/index.html` 참고. **배정 포트: 50057**.
