"""게이트웨이 통합 테스트 (서버 스트리밍 → SSE).

브라우저 대신 TestClient 로 REST 엔드포인트를 호출하고, 그 호출이 내부
gRPC 서버 스트리밍으로 전달되어 N개의 메시지가 SSE 로 흘러나오는지
end-to-end 로 확인한다.
"""

import json

from fastapi.testclient import TestClient

from app.main import app


def _parse_sse(text: str) -> tuple[list[dict], dict | None, dict | None]:
    """SSE 본문을 (메시지목록, done이벤트, error이벤트) 로 파싱한다."""
    messages: list[dict] = []
    done: dict | None = None
    error: dict | None = None
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event = "message"
        data = None
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data = json.loads(line[len("data:"):].strip())
        if data is None:
            continue
        if event == "done":
            done = data
        elif event == "error":
            error = data
        else:
            messages.append(data)
    return messages, done, error


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_stream_receives_all_messages(grpc_server_factory):
    # 서버가 정확히 3개를 stream 으로 보낸다 -> 클라이언트도 3개 모두 받아야 한다.
    grpc_server_factory(count=3)
    with TestClient(app) as client:
        resp = client.post("/chat-stream", json={"message": "안녕"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    messages, done, error = _parse_sse(resp.text)
    assert error is None
    # 3개 모두 수신, 순서 보존, 요청 메시지가 그대로 전달됨
    assert [m["message"] for m in messages] == ["안녕 #0", "안녕 #1", "안녕 #2"]
    assert [m["index"] for m in messages] == [0, 1, 2]
    assert done == {"count": 3}


def test_chat_stream_streams_incrementally(grpc_server_factory):
    # httpx 스트리밍으로 라인 단위 수신을 확인한다(본문을 한 번에 받지 않음).
    grpc_server_factory(count=5)
    received: list[str] = []
    with TestClient(app) as client:
        with client.stream("POST", "/chat-stream", json={"message": "스트림"}) as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    payload = json.loads(line[len("data:"):].strip())
                    if "message" in payload:
                        received.append(payload["message"])
    assert received == [f"스트림 #{i}" for i in range(5)]


def test_chat_stream_empty_stream(grpc_server_factory):
    # 서버가 0개를 보내도 게이트웨이는 200 + done(count=0) 으로 정상 종료한다.
    grpc_server_factory(count=0)
    with TestClient(app) as client:
        resp = client.post("/chat-stream", json={"message": "없음"})
    assert resp.status_code == 200
    messages, done, error = _parse_sse(resp.text)
    assert messages == []
    assert done == {"count": 0}


def test_chat_stream_backend_unavailable_returns_503():
    # 백엔드 서버를 띄우지 않으면 첫 메시지 수신 전에 UNAVAILABLE -> 503 매핑.
    with TestClient(app) as client:
        resp = client.post("/chat-stream", json={"message": "Hello"})
    assert resp.status_code == 503


def test_validation_rejects_empty_message():
    with TestClient(app) as client:
        resp = client.post("/chat-stream", json={"message": ""})
    assert resp.status_code == 422  # Pydantic 검증 실패
