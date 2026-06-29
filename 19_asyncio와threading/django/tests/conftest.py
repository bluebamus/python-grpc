"""Django 통합 테스트용 픽스처.

gRPC가 없는 순수 HTTP 샘플이라 서버 기동 픽스처가 필요 없다. consumer
데몬 스레드는 앱 로드 시(apps.ready) 1회 기동되지만, 테스트에서도
명시적으로 한 번 더 호출해 둔다(가드로 중복 기동되지 않는다).
"""

import time

import pytest

from gateway import worker


@pytest.fixture(autouse=True)
def ensure_worker_started():
    # 중복 기동 방지 가드 덕에 여러 번 불러도 스레드는 하나만 돈다.
    worker.start_worker()
    yield


def poll_until_done(client, task_id: int, timeout: float = 5.0) -> dict:
    """consumer가 작업을 처리 완료(status == done)할 때까지 폴링한다."""
    deadline = time.time() + timeout
    body: dict = {}
    while time.time() < deadline:
        resp = client.get(f"/tasks/{task_id}")
        assert resp.status_code == 200
        body = resp.json()
        if body["status"] == "done":
            return body
        time.sleep(0.02)
    raise AssertionError(f"task {task_id} not done in time: {body}")
