"""FastAPI 게이트웨이 앱 (양방향 스트리밍).

WebSocket `/ws/chat` 을 노출하고, 들어온 메시지를 gRPC 양방향 스트림으로
중계한 뒤 서버 응답을 다시 WebSocket 으로 돌려준다.

까다로운 부분은 "비동기 WebSocket" 과 "동기 gRPC 양방향 스트림"을 잇는 일이다.
- gRPC 동기 스텁은 요청 *이터레이터* 를 요구한다. 외부(WebSocket)에서 실시간으로
  도착하는 메시지를 이터레이터로 만들기 위해 **스레드세이프 큐**로 제너레이터를
  구동한다(`request_gen` 이 큐에서 꺼내 yield).
- gRPC 호출(블로킹)은 별도 **백그라운드 스레드**에서 돌리고, 응답을 또 다른 큐에
  넣는다. 이벤트 루프는 `run_in_executor` 로 그 큐를 비동기적으로 소비한다.
- reader(웹소켓→요청큐)와 writer(응답큐→웹소켓)를 `asyncio.gather` 로 동시에
  돌려 진짜 양방향으로 동작하게 한다.
"""

import asyncio
import queue
import threading
from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

import messages_pb2
from app.grpc_client import GrpcClient
from app.schemas import HealthResponse

# 큐 종료를 알리는 센티넬.
_SENTINEL = object()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 기동 시 채널을 한 번 열고, 종료 시 닫는다.
    client = GrpcClient()
    client.connect()
    app.state.grpc = client
    try:
        yield
    finally:
        client.close()


app = FastAPI(title="gRPC 양방향 스트리밍 게이트웨이", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    client: GrpcClient = websocket.app.state.grpc
    loop = asyncio.get_running_loop()

    # 게이트웨이 -> gRPC 로 보낼 요청을 담는 큐 (요청 제너레이터를 큐로 구동).
    send_q: "queue.Queue" = queue.Queue()
    # gRPC -> 게이트웨이 로 받은 응답을 담는 큐.
    recv_q: "queue.Queue" = queue.Queue()

    def request_gen():
        """큐에서 꺼내 ChatMessage 로 yield. None(센티넬)이면 스트림 종료."""
        while True:
            item = send_q.get()
            if item is None:
                return
            yield messages_pb2.ChatMessage(message=item)

    def run_stream():
        """별도 스레드에서 블로킹 양방향 호출을 돌리고 응답을 recv_q 로 흘린다."""
        try:
            for response in client.chat(request_gen()):
                recv_q.put(("msg", response.message))
        except grpc.RpcError as exc:
            recv_q.put(("err", exc.details() or str(exc.code())))
        finally:
            recv_q.put(_SENTINEL)

    stream_thread = threading.Thread(target=run_stream, daemon=True)
    stream_thread.start()

    async def reader():
        """WebSocket 에서 받은 텍스트를 요청 큐로 밀어 넣는다."""
        try:
            while True:
                text = await websocket.receive_text()
                send_q.put(text)
        except WebSocketDisconnect:
            pass
        finally:
            # 더 보낼 요청이 없음을 알려 gRPC 요청 스트림을 닫는다(half-close).
            send_q.put(None)

    async def writer():
        """응답 큐를 비동기로 소비해 WebSocket 으로 돌려준다."""
        while True:
            item = await loop.run_in_executor(None, recv_q.get)
            if item is _SENTINEL:
                return
            kind, payload = item
            try:
                if kind == "msg":
                    await websocket.send_text(payload)
                else:  # "err"
                    await websocket.send_text(f"error: {payload}")
            except (WebSocketDisconnect, RuntimeError):
                return

    try:
        await asyncio.gather(reader(), writer())
    finally:
        # 정리: 스트림 스레드가 끝나도록 센티넬을 보장하고 join.
        send_q.put(None)
        await loop.run_in_executor(None, stream_thread.join)
        try:
            await websocket.close()
        except RuntimeError:
            pass
