"""E2E 하니스 게이트웨이 (FastAPI).

실제 브라우저가 소비할 수 있도록:
- GET /            : EventSource(SSE) 와 WebSocket 을 사용하는 클라이언트 HTML 페이지(동일 출처)
- GET /sse         : gRPC 서버 스트리밍(ServerStream) → SSE(text/event-stream) 매핑
- WS  /ws          : gRPC 양방향(BiDi) ↔ WebSocket 브리지

샘플(3_ServerStreaming / 5_Bidirectional)의 게이트웨이 동작을 브라우저 관점에서
검증하기 위한 자족적(self-contained) 하니스다.
"""

import asyncio
import json
import os
import queue
import threading

import grpc
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse

from app import proto  # noqa: F401
import chat_pb2
import chat_pb2_grpc

GRPC_TARGET = os.environ.get("E2E_GRPC_TARGET", "localhost:50071")

app = FastAPI(title="gRPC 샘플 E2E (Playwright) 하니스")


def _stub() -> chat_pb2_grpc.ChatServiceStub:
    channel = grpc.insecure_channel(GRPC_TARGET)
    return chat_pb2_grpc.ChatServiceStub(channel)


INDEX_HTML = """<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"><title>gRPC E2E (SSE/WebSocket)</title></head>
<body>
  <h1>gRPC 샘플 브라우저 E2E</h1>

  <section>
    <h2>서버 스트리밍 → SSE</h2>
    <button id="start-sse">start SSE</button>
    <span id="sse-status">idle</span>
    <ul id="sse-list"></ul>
  </section>

  <section>
    <h2>양방향 → WebSocket</h2>
    <button id="start-ws">start WS</button>
    <span id="ws-status">idle</span>
    <ul id="ws-list"></ul>
  </section>

  <script>
    // --- SSE: EventSource 로 gRPC 서버 스트리밍 결과 소비 ---
    document.getElementById('start-sse').addEventListener('click', () => {
      document.getElementById('sse-status').textContent = 'streaming';
      const es = new EventSource('/sse?message=' + encodeURIComponent('hello|4'));
      es.addEventListener('message', (e) => {
        const data = JSON.parse(e.data);
        const li = document.createElement('li');
        li.className = 'sse-item';
        li.textContent = data.message;
        document.getElementById('sse-list').appendChild(li);
      });
      es.addEventListener('done', () => {
        document.getElementById('sse-status').textContent = 'done';
        es.close();
      });
      es.addEventListener('error', () => {
        document.getElementById('sse-status').textContent = 'error';
        es.close();
      });
    });

    // --- WebSocket: gRPC 양방향 브리지와 메시지 교환 ---
    document.getElementById('start-ws').addEventListener('click', () => {
      document.getElementById('ws-status').textContent = 'connecting';
      const ws = new WebSocket('ws://' + location.host + '/ws');
      const toSend = ['a', 'b', 'c'];
      let received = 0;
      ws.onopen = () => {
        document.getElementById('ws-status').textContent = 'open';
        toSend.forEach((m) => ws.send(m));
      };
      ws.onmessage = (e) => {
        const li = document.createElement('li');
        li.className = 'ws-item';
        li.textContent = e.data;
        document.getElementById('ws-list').appendChild(li);
        received += 1;
        if (received === toSend.length) {
          document.getElementById('ws-status').textContent = 'done';
          ws.close();
        }
      };
      ws.onerror = () => { document.getElementById('ws-status').textContent = 'error'; };
    });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sse")
def sse(message: str):
    """gRPC 서버 스트리밍을 SSE 로 중계한다."""

    def event_stream():
        stub = _stub()
        try:
            for reply in stub.ServerStream(chat_pb2.ChatMessage(message=message)):
                yield f"event: message\ndata: {json.dumps({'message': reply.message})}\n\n"
            yield "event: done\ndata: {}\n\n"
        except grpc.RpcError as exc:
            yield f"event: error\ndata: {json.dumps({'detail': exc.details()})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    """WebSocket ↔ gRPC 양방향 스트림 브리지."""
    await websocket.accept()
    loop = asyncio.get_running_loop()
    send_q: "queue.Queue[object]" = queue.Queue()   # 브라우저 → gRPC 요청
    recv_q: "asyncio.Queue[object]" = asyncio.Queue()  # gRPC 응답 → 브라우저
    _SENTINEL = object()

    def request_iter():
        while True:
            item = send_q.get()
            if item is _SENTINEL:
                return
            yield chat_pb2.ChatMessage(message=item)

    def pump_responses():
        stub = _stub()
        try:
            for reply in stub.BiDi(request_iter()):
                loop.call_soon_threadsafe(recv_q.put_nowait, reply.message)
        except grpc.RpcError as exc:
            loop.call_soon_threadsafe(recv_q.put_nowait, {"error": exc.details()})
        finally:
            loop.call_soon_threadsafe(recv_q.put_nowait, _SENTINEL)

    worker = threading.Thread(target=pump_responses, daemon=True)
    worker.start()

    async def browser_to_grpc():
        try:
            while True:
                msg = await websocket.receive_text()
                send_q.put(msg)
        except WebSocketDisconnect:
            send_q.put(_SENTINEL)

    async def grpc_to_browser():
        while True:
            item = await recv_q.get()
            if item is _SENTINEL:
                break
            await websocket.send_text(item if isinstance(item, str) else json.dumps(item))

    reader = asyncio.create_task(browser_to_grpc())
    try:
        await grpc_to_browser()
    finally:
        send_q.put(_SENTINEL)
        reader.cancel()
