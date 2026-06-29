"""FastAPI 게이트웨이 앱.

REST 엔드포인트(POST /divide)를 노출하고, 내부적으로 gRPC 백엔드를 호출한다.
이 예제의 주제는 **에러 핸들링**이다: gRPC 상태코드(StatusCode)를 의미가
맞는 HTTP 상태코드로 충실히 매핑하고, 서버가 내려준 에러 상세(details)도
응답 본문에 함께 담아 클라이언트가 원인을 알 수 있게 한다.
"""

import time
from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.grpc_client import GrpcClient
from app.schemas import DivideRequest, DivideResponse

# gRPC StatusCode -> HTTP status 매핑 표.
# 실무에서 게이트웨이는 백엔드의 의미를 HTTP 의미로 번역해야 한다.
# grpc.StatusCode 16종 전체를 명시적으로 매핑한다(공식 grpc-gateway 규약 기준).
_GRPC_TO_HTTP: dict[grpc.StatusCode, int] = {
    grpc.StatusCode.OK: 200,
    grpc.StatusCode.CANCELLED: 499,             # Client Closed Request
    grpc.StatusCode.UNKNOWN: 500,
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.ALREADY_EXISTS: 409,
    grpc.StatusCode.PERMISSION_DENIED: 403,
    grpc.StatusCode.UNAUTHENTICATED: 401,
    grpc.StatusCode.RESOURCE_EXHAUSTED: 429,
    grpc.StatusCode.FAILED_PRECONDITION: 400,
    grpc.StatusCode.ABORTED: 409,
    grpc.StatusCode.OUT_OF_RANGE: 400,
    grpc.StatusCode.UNIMPLEMENTED: 501,
    grpc.StatusCode.INTERNAL: 500,
    grpc.StatusCode.UNAVAILABLE: 503,
    grpc.StatusCode.DATA_LOSS: 500,
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


app = FastAPI(title="gRPC 에러핸들링 게이트웨이", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/divide", response_model=DivideResponse)
def divide(req: DivideRequest):
    client: GrpcClient = app.state.grpc
    started = time.perf_counter()
    try:
        quotient = client.divide(req.dividend, req.divisor)
    except grpc.RpcError as exc:
        # 핵심: gRPC 에러를 HTTP 로 변환한다.
        # 서버는 divisor=0 일 때 INVALID_ARGUMENT 로 abort -> HTTP 400.
        code = exc.code()
        http_status = _GRPC_TO_HTTP.get(code, 500)
        # 에러 상세(details)도 응답에 포함해 클라이언트가 원인을 알 수 있게 한다.
        return JSONResponse(
            status_code=http_status,
            content={
                "error": {
                    "grpc_status": code.name,
                    "http_status": http_status,
                    "detail": exc.details(),
                }
            },
        )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return DivideResponse(quotient=quotient, elapsed_ms=round(elapsed_ms, 2))
