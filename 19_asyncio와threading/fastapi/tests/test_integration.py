"""asyncio 작업 큐 통합 테스트 (순수 HTTP).

브라우저 대신 TestClient/AsyncClient로 REST 엔드포인트를 호출하고,
producer가 넣은 작업을 백그라운드 consumer 코루틴이 처리하는지를
end-to-end로 확인한다. gRPC는 사용하지 않는다.
"""

import asyncio
import time

import httpx
from fastapi.testclient import TestClient

from app.main import app
from conftest import poll_until_done


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_submit_then_consumer_processes():
    # POST로 작업 투입 -> consumer가 처리 -> GET으로 done/result 확인
    with TestClient(app) as client:
        resp = client.post("/tasks", json={"payload": "hello"})
        assert resp.status_code == 202
        body = resp.json()
        assert body["queued"] is True
        task_id = body["task_id"]

        done = poll_until_done(client, task_id)
    assert done["status"] == "done"
    assert done["result"] == "HELLO"  # _blocking_process가 대문자로 변환


def test_stats_processed_count_increases():
    # 여러 작업 투입 시 /stats의 processed 카운트가 그만큼 증가한다.
    with TestClient(app) as client:
        before = client.get("/stats").json()["processed"]

        task_ids = []
        for i in range(5):
            r = client.post("/tasks", json={"payload": f"job-{i}"})
            task_ids.append(r.json()["task_id"])
        for tid in task_ids:
            poll_until_done(client, tid)

        after = client.get("/stats").json()
    assert after["processed"] - before == 5
    assert after["pending"] == 0


def test_validation_rejects_empty_payload():
    with TestClient(app) as client:
        resp = client.post("/tasks", json={"payload": ""})
    assert resp.status_code == 422  # Pydantic min_length 검증 실패


def test_unknown_task_returns_404():
    with TestClient(app) as client:
        resp = client.get("/tasks/999999")
    assert resp.status_code == 404


def test_concurrent_submissions_do_not_block_event_loop():
    """비동기 처리가 이벤트 루프를 막지 않음을 보인다.

    10개의 POST를 동시에(asyncio.gather) 발사한다. 만약 이벤트 루프가
    어느 한 작업에서 블로킹된다면 동시 요청이 직렬화되어 모두 완료되지
    못한다. consumer가 블로킹 작업을 to_thread로 처리하고 put/get이
    await 기반이라, 모든 요청이 받아들여지고 전부 done이 된다.

    dev 의존성에 pytest-asyncio가 없으므로 async 시나리오를
    asyncio.run으로 직접 구동한다(별도 플러그인 불필요).
    """
    asyncio.run(_concurrent_scenario())


async def _concurrent_scenario():
    # ASGITransport로 앱을 인프로세스 호출. lifespan_context로 consumer를 띄운다.
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # 10개 동시 투입
            posts = [ac.post("/tasks", json={"payload": f"c-{i}"}) for i in range(10)]
            responses = await asyncio.gather(*posts)
            task_ids = [r.json()["task_id"] for r in responses]
            assert all(r.status_code == 202 for r in responses)

            # 모두 done이 될 때까지 폴링(동시 조회)
            deadline = time.time() + 5.0
            statuses: list = []
            while time.time() < deadline:
                gets = [ac.get(f"/tasks/{tid}") for tid in task_ids]
                results = await asyncio.gather(*gets)
                statuses = [r.json()["status"] for r in results]
                if all(s == "done" for s in statuses):
                    break
                await asyncio.sleep(0.02)
            assert all(s == "done" for s in statuses), statuses
