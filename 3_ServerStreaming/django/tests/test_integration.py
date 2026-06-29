"""Django 게이트웨이 통합 테스트 (서버 스트리밍 → SSE)."""

import json

from django.test import Client

client = Client()


def _collect(resp) -> str:
    """StreamingHttpResponse 의 streaming_content 를 모아 문자열로 만든다."""
    return b"".join(resp.streaming_content).decode("utf-8")


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
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_stream_receives_all_messages(grpc_server_factory):
    # 서버가 정확히 3개를 stream 으로 보낸다 -> 클라이언트도 3개 모두 받아야 한다.
    grpc_server_factory(count=3)
    resp = client.post("/chat-stream", data={"message": "안녕"}, content_type="application/json")
    assert resp.status_code == 200
    assert resp["content-type"].startswith("text/event-stream")

    messages, done, error = _parse_sse(_collect(resp))
    assert error is None
    assert [m["message"] for m in messages] == ["안녕 #0", "안녕 #1", "안녕 #2"]
    assert [m["index"] for m in messages] == [0, 1, 2]
    assert done == {"count": 3}


def test_chat_stream_streams_each_chunk(grpc_server_factory):
    # streaming_content 가 메시지마다 별도 청크로 끊겨 나오는지 확인(스트리밍 증거).
    grpc_server_factory(count=5)
    resp = client.post("/chat-stream", data={"message": "스트림"}, content_type="application/json")
    assert resp.status_code == 200

    received: list[str] = []
    for chunk in resp.streaming_content:
        block = chunk.decode("utf-8")
        for line in block.splitlines():
            if line.startswith("data:"):
                payload = json.loads(line[len("data:"):].strip())
                if "message" in payload:
                    received.append(payload["message"])
    assert received == [f"스트림 #{i}" for i in range(5)]


def test_chat_stream_empty_stream(grpc_server_factory):
    # 서버가 0개를 보내도 200 + done(count=0) 으로 정상 종료한다.
    grpc_server_factory(count=0)
    resp = client.post("/chat-stream", data={"message": "없음"}, content_type="application/json")
    assert resp.status_code == 200
    messages, done, error = _parse_sse(_collect(resp))
    assert messages == []
    assert done == {"count": 0}


def test_chat_stream_backend_unavailable_returns_503():
    # 백엔드 서버를 띄우지 않으면 첫 메시지 수신 전에 UNAVAILABLE -> 503 매핑.
    from gateway import grpc_client

    grpc_client.reset_client()
    resp = client.post("/chat-stream", data={"message": "Hello"}, content_type="application/json")
    grpc_client.reset_client()
    assert resp.status_code == 503


def test_validation_rejects_empty_message():
    resp = client.post("/chat-stream", data={"message": ""}, content_type="application/json")
    assert resp.status_code == 422
