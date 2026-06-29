# FastAPI asyncio 작업 큐 (19_asyncio와threading)

동시성 데모 `server_asyncio.py`(asyncio.Queue 기반 producer/consumer)를
웹 서비스로 실무화한 샘플입니다. HTTP 요청이 **producer**가 되어
`asyncio.Queue`에 작업을 넣고, lifespan에서 기동된 백그라운드 **consumer
코루틴**이 큐를 비우며 처리합니다. 단일 이벤트 루프 위에서 요청 처리와
작업 소비가 협력적으로 동시에 진행되는 **asyncio 동시성 모델**을 보여줍니다.

## 구조

```
fastapi/
├── app/
│   ├── worker.py   # asyncio.Queue + consumer 코루틴 + 인메모리 작업 저장소
│   ├── schemas.py  # Pydantic 요청/응답
│   ├── config.py   # 설정(환경변수)
│   └── main.py     # FastAPI 앱(lifespan에서 consumer 기동/셧다운)
├── tests/          # 순수 HTTP 통합 테스트
└── docs/index.html # asyncio vs threading 가이드 문서
```

## 엔드포인트

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| GET | `/health` | 헬스체크 |
| POST | `/tasks` | `{"payload":"..."}` 투입(producer) → `{"task_id":..,"queued":true}` |
| GET | `/tasks/{task_id}` | 작업 상태/결과 조회 (`queued`/`processing`/`done`) |
| GET | `/stats` | 처리 카운트 등 통계 |

## 설치 & 실행

```bash
uv sync

# 서버 기동
uv run uvicorn app.main:app --reload

# 작업 투입
curl -X POST localhost:8000/tasks -H "content-type: application/json" -d '{"payload":"hello"}'
# 결과 조회
curl localhost:8000/tasks/1
curl localhost:8000/stats
```

## 테스트

```bash
uv run pytest
```

순수 HTTP로 producer→queue→consumer 흐름을 검증합니다. 특히
`test_concurrent_submissions_do_not_block_event_loop`는 동시 투입한 작업이
이벤트 루프를 막지 않고 모두 처리됨을 보입니다. 자세한 설명은
`docs/index.html` 참고.
