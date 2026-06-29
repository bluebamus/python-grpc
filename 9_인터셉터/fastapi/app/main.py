"""FastAPI 게이트웨이 앱.

REST 엔드포인트(POST /echo)를 노출하고, 내부적으로 gRPC 백엔드를 호출한다.
호출 경로에는 클라이언트 인터셉터가 끼어 있어 로깅과 x-request-id 주입을
자동으로 처리한다. gRPC 상태코드는 HTTP 상태코드로 매핑한다.
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
    grpc.StatusCode.UNAVAILABLE: 503,
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.PERMISSION_DENIED: 403,
    grpc.StatusCode.UNAUTHENTICATED: 401,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 기동 시 채널(+인터셉터)을 한 번 열고, 종료 시 닫는다.
    client = GrpcClient()
    client.connect()
    app.state.grpc = client
    try:
        yield
    finally:
        client.close()


app = FastAPI(title="gRPC 인터셉터 게이트웨이", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/echo", response_model=EchoResponse)
def echo(req: EchoRequest) -> EchoResponse:
    client: GrpcClient = app.state.grpc
    started = time.perf_counter()
    try:
        message, request_id = client.echo(req.message)
    except grpc.RpcError as exc:
        http_status = _GRPC_TO_HTTP.get(exc.code(), 500)
        raise HTTPException(status_code=http_status, detail=exc.details()) from exc
    elapsed_ms = (time.perf_counter() - started) * 1000
    return EchoResponse(message=message, request_id=request_id, elapsed_ms=round(elapsed_ms, 2))
