"""게이트웨이 통합 테스트 (양방향 스트리밍).

브라우저 대신 TestClient 의 websocket_connect 로 WebSocket 을 열고, 메시지
N개를 보낸 뒤 에코 N개를 받는지 end-to-end 로 확인한다. WebSocket 으로 받은
메시지는 내부 gRPC 양방향 스트림으로 중계된다.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ws_chat_echoes_each_message(echo_server):
    with TestClient(app) as client:
        with client.websocket_connect("/ws/chat") as ws:
            # 3개 전송
            sent = [f"msg{i}" for i in range(3)]
            for text in sent:
                ws.send_text(text)
            # 3개 에코 수신 (같은 순서)
            received = [ws.receive_text() for _ in range(3)]
    assert received == [f"echo: {text}" for text in sent]


def test_ws_chat_single_message(echo_server):
    with TestClient(app) as client:
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text("hello")
            reply = ws.receive_text()
    assert reply == "echo: hello"
