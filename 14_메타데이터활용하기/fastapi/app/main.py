"""FastAPI 게이트웨이 앱.

REST 엔드포인트(POST /echo)를 노출하고, 내부적으로 gRPC 백엔드를 호출한다.
이 예제의 주제는 **메타데이터**다:

- 들어온 HTTP 헤더 `Authorization`, `X-Request-Id` 를 gRPC 메타데이터로 변환해 주입.
- `X-Request-Id` 가 없으면 게이트웨이가 UUID 로 생성(상관관계 추적용).
- 서버가 trailing metadata 로 돌려준 값을 HTTP 응답 바디/헤더로 노출.

gRPC 상태코드는 HTTP 상태코드로 매핑해 외부에는 표준 HTTP 의미로 응답한다.
"""

import time
import uuid
from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, Header, HTTPException, Response

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
    # 앱 기동 시 채널을 한 번 열고, 종료 시 닫는다.
    client = GrpcClient()
    client.connect()
    app.state.grpc = client
    try:
        yield
    finally:
        client.close()


app = FastAPI(title="gRPC 메타데이터 게이트웨이", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/echo", response_model=EchoResponse)
def echo(
    req: EchoRequest,
    response: Response,
    authorization: str | None = Header(default=None),
    x_request_id: str | None = Header(default=None),
) -> EchoResponse:
    client: GrpcClient = app.state.grpc

    # X-Request-Id 가 없으면 게이트웨이가 생성한다(분산 추적 상관키).
    request_id = x_request_id or f"gw-{uuid.uuid4().hex}"

    started = time.perf_counter()
    try:
        result = client.echo(
            message=req.message,
            request_id=request_id,
            authorization=authorization,
        )
    except grpc.RpcError as exc:
        http_status = _GRPC_TO_HTTP.get(exc.code(), 500)
        raise HTTPException(status_code=http_status, detail=exc.details()) from exc
    elapsed_ms = (time.perf_counter() - started) * 1000

    # 서버가 보낸 메타데이터를 HTTP 응답 헤더로도 노출한다.
    response.headers["X-Request-Id"] = result.request_id
    response.headers["X-Auth-Present"] = result.auth_present

    return EchoResponse(
        message=result.message,
        request_id=result.request_id,
        elapsed_ms=round(elapsed_ms, 2),
    )
