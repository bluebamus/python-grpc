"""FastAPI 게이트웨이 앱.

REST 엔드포인트(POST /unary)를 노출하고, 내부적으로 gRPC 백엔드를 호출한다.
gRPC 상태코드를 HTTP 상태코드로 매핑해 외부에는 표준 HTTP 의미로 응답한다.
"""

import time
from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, HTTPException

from app.grpc_client import GrpcClient
from app.schemas import UnaryRequest, UnaryResponse

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


app = FastAPI(title="gRPC 재시도 게이트웨이", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/unary", response_model=UnaryResponse)
def unary(req: UnaryRequest) -> UnaryResponse:
    client: GrpcClient = app.state.grpc
    started = time.perf_counter()
    try:
        message = client.unary_call(req.message)
    except grpc.RpcError as exc:
        # 재시도를 모두 소진한 뒤에도 실패하면 여기로 온다.
        http_status = _GRPC_TO_HTTP.get(exc.code(), 500)
        raise HTTPException(status_code=http_status, detail=exc.details()) from exc
    elapsed_ms = (time.perf_counter() - started) * 1000
    return UnaryResponse(message=message, elapsed_ms=round(elapsed_ms, 2))
