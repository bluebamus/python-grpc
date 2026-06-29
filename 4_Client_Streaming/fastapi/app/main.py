"""FastAPI 게이트웨이 앱.

REST 엔드포인트(POST /stream-data)를 노출하고, 내부적으로 gRPC 백엔드를
**클라이언트 스트리밍**으로 호출한다. 요청 본문의 items 리스트를 gRPC 요청
스트림으로 변환해 보내고, 서버가 집계한 단일 응답을 HTTP 응답으로 돌려준다.
gRPC 상태코드를 HTTP 상태코드로 매핑해 외부에는 표준 HTTP 의미로 응답한다.
"""

import time
from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, HTTPException

from app.grpc_client import GrpcClient
from app.schemas import StreamDataRequest, StreamDataResponse

# gRPC StatusCode -> HTTP status 매핑.
# 실무에서 게이트웨이는 백엔드의 의미를 HTTP 의미로 번역해야 한다.
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


app = FastAPI(title="gRPC 클라이언트 스트리밍 게이트웨이", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/stream-data", response_model=StreamDataResponse)
def stream_data(req: StreamDataRequest) -> StreamDataResponse:
    client: GrpcClient = app.state.grpc
    started = time.perf_counter()
    try:
        result = client.stream_data(req.items)
    except grpc.RpcError as exc:
        http_status = _GRPC_TO_HTTP.get(exc.code(), 500)
        raise HTTPException(status_code=http_status, detail=exc.details()) from exc
    elapsed_ms = (time.perf_counter() - started) * 1000
    return StreamDataResponse(
        result=result,
        count=len(req.items),
        elapsed_ms=round(elapsed_ms, 2),
    )
