"""FastAPI 게이트웨이 앱.

REST 엔드포인트를 노출하고, 내부적으로 gRPC 백엔드를 호출한다.
gRPC 상태코드를 HTTP 상태코드로 매핑해 외부에는 표준 HTTP 의미로 응답한다.

엔드포인트:
- GET  /health    : 헬스 체크
- POST /echo       : Echo 비즈니스 호출
- GET  /services   : 서버 리플렉션으로 서비스 목록 조회 (이 예제의 주제)
"""

from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, HTTPException

from app.grpc_client import GrpcClient
from app.schemas import EchoRequest, EchoResponse, ServicesResponse

# gRPC StatusCode -> HTTP status 매핑.
# 실무에서 게이트웨이는 백엔드의 의미를 HTTP 의미로 번역해야 한다.
_GRPC_TO_HTTP = {
    grpc.StatusCode.UNAVAILABLE: 503,
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.PERMISSION_DENIED: 403,
    grpc.StatusCode.UNAUTHENTICATED: 401,
    grpc.StatusCode.UNIMPLEMENTED: 501,
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


app = FastAPI(title="gRPC 리플렉션 게이트웨이", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/echo", response_model=EchoResponse)
def echo(req: EchoRequest) -> EchoResponse:
    client: GrpcClient = app.state.grpc
    try:
        message = client.echo(req.message)
    except grpc.RpcError as exc:
        http_status = _GRPC_TO_HTTP.get(exc.code(), 500)
        raise HTTPException(status_code=http_status, detail=exc.details()) from exc
    return EchoResponse(message=message)


@app.get("/services", response_model=ServicesResponse)
def services() -> ServicesResponse:
    """서버 리플렉션으로 서버가 노출하는 서비스 목록을 조회한다.

    클라이언트가 .proto 를 미리 갖고 있지 않아도, 서버에 직접 물어
    어떤 서비스가 있는지 동적으로 발견할 수 있다.
    """
    client: GrpcClient = app.state.grpc
    try:
        names = client.list_services()
    except grpc.RpcError as exc:
        http_status = _GRPC_TO_HTTP.get(exc.code(), 500)
        raise HTTPException(status_code=http_status, detail=exc.details()) from exc
    return ServicesResponse(services=names)
