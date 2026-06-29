"""E2E 픽스처: gRPC 서버 + uvicorn 게이트웨이를 백그라운드로 기동.

Playwright 의 `page` 픽스처(pytest-playwright 제공)가 이 live 서버에 접속한다.
"""

import os
import threading
import time

import pytest

GRPC_PORT = 50071
HTTP_PORT = 8071

# 앱이 import 시점에 읽는 gRPC 타깃을 테스트 포트로 고정한다.
os.environ.setdefault("E2E_GRPC_TARGET", f"localhost:{GRPC_PORT}")


@pytest.fixture(scope="session")
def grpc_server():
    from app.grpc_server import start_server

    server = start_server(GRPC_PORT)
    yield server
    server.stop(grace=None)


@pytest.fixture(scope="session")
def live_server(grpc_server):
    import uvicorn

    from app.main import app

    config = uvicorn.Config(app, host="127.0.0.1", port=HTTP_PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # 서버가 뜰 때까지 대기
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("uvicorn 서버 기동 실패")

    yield f"http://127.0.0.1:{HTTP_PORT}"

    server.should_exit = True
    thread.join(timeout=5)
