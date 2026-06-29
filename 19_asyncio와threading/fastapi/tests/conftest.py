"""통합 테스트 공용 헬퍼.

gRPC가 없는 순수 HTTP 샘플이므로 별도 서버 기동 픽스처가 필요 없다.
TestClient의 컨텍스트 매니저가 lifespan을 실행해 consumer 코루틴을
띄우고, 종료 시 그레이스풀 셧다운까지 처리한다.
"""

import time


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
