# Django threading 작업 큐 (19_asyncio와threading)

동시성 데모 `server_threading.py`(queue.Queue + threading 기반
producer/consumer)를 웹 서비스로 실무화한 샘플입니다. HTTP 요청이
**producer**가 되어 `queue.Queue`에 작업을 넣고, 앱 로드 시 1회 기동된
데몬 **consumer 스레드**가 차단형 `get()`으로 큐를 비우며 처리합니다.
**threading 동시성 모델**을 보여줍니다.

## 구조

```
django/
├── manage.py
├── config/            # settings, urls, wsgi
├── gateway/           # app: views, urls, worker(queue.Queue+thread), apps
├── tests/             # 순수 HTTP 통합 테스트
└── docs/index.html    # asyncio vs threading 가이드 문서
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

# 서버 기동 (consumer 스레드는 앱 로드 시 자동 기동)
uv run python manage.py runserver

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

consumer 스레드는 `gateway/apps.py`의 `ready()`에서 `start_worker()`로
1회 기동되며, 중복 기동 방지 가드가 들어 있습니다. 자세한 설명은
`docs/index.html` 참고.
