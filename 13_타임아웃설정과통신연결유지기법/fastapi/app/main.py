"""FastAPI 게이트웨이 앱.

REST 엔드포인트(POST /echo)를 노출하고, 내부적으로 gRPC 백엔드를 호출한다.
호출에는 per-call deadline 을 적용하며, 백엔드가 데드라인 안에 응답하지 못하면
gRPC 가 `DEADLINE_EXCEEDED` 를 던지고 게이트웨이는 이를 HTTP 504 로 매핑한다.
"""

import time
from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, HTTPException

from app.grpc_client import GrpcClient
from app.schemas import EchoRequest, EchoResponse

# gRPC StatusCode -> HTTP status 매핑.
# 실무에서 게이트웨이는 백엔드의 의미를 HTTP 의미로 번역해야 한다.
_GRPC_TO_HTTP = {
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,  # 데드라인 초과 → Gateway Timeout
    grpc.StatusCode.UNAVAILABLE: 503,
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.PERMISSION_DENIED: 403,
    grpc.StatusCode.UNAUTHENTICATED: 401,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 기동 시 채널을 한 번 열고(keepalive 옵션 포함), 종료 시 닫는다.
    client = GrpcClient()
    client.connect()
    app.state.grpc = client
    try:
        yield
    finally:
        client.close()


app = FastAPI(title="gRPC 타임아웃·keepalive 게이트웨이", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/echo", response_model=EchoResponse)
def echo(req: EchoRequest) -> EchoResponse:
    client: GrpcClient = app.state.grpc
    started = time.perf_counter()
    try:
        message = client.echo(req.message, deadline_ms=req.deadline_ms)
    except grpc.RpcError as exc:
        # 데드라인 초과 등 RPC 실패는 여기로 온다.
        http_status = _GRPC_TO_HTTP.get(exc.code(), 500)
        raise HTTPException(status_code=http_status, detail=exc.details()) from exc
    elapsed_ms = (time.perf_counter() - started) * 1000
    return EchoResponse(message=message, elapsed_ms=round(elapsed_ms, 2))
