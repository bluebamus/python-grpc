"""FastAPI 게이트웨이 앱 (서버 스트리밍 → HTTP 스트리밍).

REST 엔드포인트(POST /chat-stream)를 노출하고, 내부적으로 gRPC 서버 스트리밍
RPC(ChatStream)를 호출한다. 요청 1개에 대해 서버가 응답을 여러 개 stream 으로
보내면, 게이트웨이는 그것을 모아서 한 번에 주지 않고 **SSE(text/event-stream)**
로 도착하는 대로 클라이언트에 흘려보낸다.

서버 스트리밍의 의미를 HTTP 로 보존하는 것이 이 예제의 핵심이다:
gRPC stream <-> HTTP chunked streaming(SSE).
"""

import json

import grpc
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager

from app.grpc_client import GrpcClient
from app.schemas import ChatRequest

# gRPC StatusCode -> HTTP status 매핑.
# 스트리밍이 시작되기 전에 발생한 오류는 이 매핑으로 일반 HTTP 에러로 응답한다.
_GRPC_TO_HTTP = {
    grpc.StatusCode.UNAVAILABLE: 503,
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.PERMISSION_DENIED: 403,
    grpc.StatusCode.UNAUTHENTICATED: 401,
}


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


app = FastAPI(title="gRPC 서버 스트리밍 게이트웨이", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _sse(data: dict) -> str:
    """dict 를 SSE 한 이벤트(`data: {json}\\n\\n`)로 직렬화한다."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/chat-stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    """서버 스트리밍을 SSE 로 중계한다.

    제너레이터가 gRPC 스트림을 순회하며 도착하는 메시지마다 SSE 이벤트를 yield 한다.
    스트림이 시작된 뒤(=이미 200 응답이 나간 뒤)에 오류가 나면 HTTP 상태코드를
    바꿀 수 없으므로, 오류를 별도 SSE 이벤트(event: error)로 클라이언트에 알린다.
    """
    client: GrpcClient = app.state.grpc

    # 첫 메시지를 받기 전에 발생하는 오류(예: 백엔드 UNAVAILABLE)는 일반 HTTP
    # 에러로 매핑할 수 있도록, 스트림을 미리 한 번 당겨본다(peek).
    stream = client.chat_stream(req.message)
    try:
        first = next(stream)
    except StopIteration:
        first = None  # 메시지가 0개인 정상 스트림
    except grpc.RpcError as exc:
        http_status = _GRPC_TO_HTTP.get(exc.code(), 500)
        raise HTTPException(status_code=http_status, detail=exc.details()) from exc

    def event_generator():
        index = 0
        if first is not None:
            yield _sse({"index": index, "message": first})
            index += 1
        try:
            for message in stream:
                yield _sse({"index": index, "message": message})
                index += 1
        except grpc.RpcError as exc:
            # 스트림 도중 실패: 상태코드는 못 바꾸므로 error 이벤트로 알린다.
            yield f"event: error\ndata: {json.dumps({'code': exc.code().name, 'detail': exc.details()}, ensure_ascii=False)}\n\n"
            return
        # 정상 종료를 알리는 done 이벤트 (총 개수 포함)
        yield f"event: done\ndata: {json.dumps({'count': index}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
