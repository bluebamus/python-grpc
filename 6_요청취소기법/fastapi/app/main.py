"""FastAPI 게이트웨이 앱.

REST 엔드포인트(POST /operation)를 노출하고, 내부적으로 gRPC 백엔드의
오래 걸리는 작업을 호출한다. 핵심 주제는 **요청 취소**다.

1) per-call 데드라인(timeout)을 적용해 호출한다. 초과 시 gRPC 가
   `DEADLINE_EXCEEDED` 를 던지고 서버 작업이 취소된다 → HTTP 504 로 매핑.
2) 클라이언트(브라우저)가 연결을 끊으면 `request.is_disconnected()` 로 감지하고
   `future.cancel()` 로 백엔드 호출을 취소해 자원 낭비를 막는다.
"""

import asyncio
import time
from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, HTTPException, Request

from app.config import settings
from app.grpc_client import GrpcClient
from app.schemas import OperationRequest, OperationResponse

# gRPC StatusCode -> HTTP status 매핑.
# 실무에서 게이트웨이는 백엔드의 의미를 HTTP 의미로 번역해야 한다.
_GRPC_TO_HTTP = {
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,  # 데드라인 초과(작업 취소됨)
    grpc.StatusCode.CANCELLED: 499,          # 클라이언트가 취소
    grpc.StatusCode.UNAVAILABLE: 503,
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


app = FastAPI(title="gRPC 요청취소 게이트웨이", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/operation", response_model=OperationResponse)
async def operation(req: OperationRequest, request: Request) -> OperationResponse:
    client: GrpcClient = app.state.grpc

    # deadline_ms 가 없으면 게이트웨이 기본값을 쓴다. gRPC timeout 은 초 단위.
    deadline_ms = req.deadline_ms or settings.default_deadline_ms
    timeout_s = deadline_ms / 1000.0

    started = time.perf_counter()
    # future 로 호출을 시작하고, 완료될 때까지 비동기로 폴링한다.
    future = client.start_operation(req.data, timeout=timeout_s)
    try:
        while not future.done():
            # 클라이언트가 연결을 끊었으면 백엔드 호출도 취소한다.
            # (취소하지 않으면 서버는 의미 없는 작업을 끝까지 수행한다.)
            if await request.is_disconnected():
                future.cancel()
                raise HTTPException(status_code=499, detail="client disconnected")
            await asyncio.sleep(settings.disconnect_poll_interval)
        # future 가 끝났다. 데드라인 초과/취소면 여기서 RpcError 가 올라온다.
        response = future.result()
    except grpc.RpcError as exc:
        http_status = _GRPC_TO_HTTP.get(exc.code(), 500)
        raise HTTPException(status_code=http_status, detail=exc.details()) from exc

    elapsed_ms = (time.perf_counter() - started) * 1000
    return OperationResponse(result=response.response_data, elapsed_ms=round(elapsed_ms, 2))
