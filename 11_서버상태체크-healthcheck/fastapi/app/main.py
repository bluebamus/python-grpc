"""FastAPI 헬스체크 게이트웨이 앱.

REST 엔드포인트를 노출하고, 내부적으로 gRPC 표준 헬스체크(Check)를 호출한다.
백엔드의 ServingStatus 와 gRPC 상태코드를 HTTP 상태코드로 매핑해, 외부에는
표준 HTTP 의미(200/503/...)로 응답한다.
"""

from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, Response

from app import proto  # noqa: F401  (proto sys.path 등록)
import health_check_pb2
from app.grpc_client import GrpcClient
from app.schemas import GrpcHealthResponse

# ServingStatus(int) -> (이름, HTTP status) 매핑.
# SERVING 만 정상(200)이고, 나머지는 모두 "서비스 불가" 의미로 503 으로 매핑한다.
_Status = health_check_pb2.HealthCheckResponse
_STATUS_TO_HTTP: dict[int, tuple[str, int]] = {
    _Status.SERVING: ("SERVING", 200),
    _Status.NOT_SERVING: ("NOT_SERVING", 503),
    _Status.SERVICE_UNKNOWN: ("SERVICE_UNKNOWN", 503),
    _Status.UNKNOWN: ("UNKNOWN", 503),
}

# gRPC StatusCode -> HTTP status 매핑(백엔드가 Check 자체를 에러로 끝낸 경우).
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


app = FastAPI(title="gRPC 헬스체크 게이트웨이", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    """게이트웨이 자체 헬스. 백엔드와 무관하게 항상 200."""
    return {"status": "ok"}


@app.get("/health/grpc", response_model=GrpcHealthResponse)
def health_grpc(response: Response, service: str = "") -> GrpcHealthResponse:
    """백엔드 gRPC 서비스의 헬스 상태를 Check 로 조회해 HTTP 로 노출한다.

    service 쿼리 파라미터를 비우면(""), 보통 "서버 전체"의 상태를 의미한다.
    """
    client: GrpcClient = app.state.grpc
    try:
        status_value = client.check(service)
    except grpc.RpcError as exc:
        # 백엔드가 모르는 서비스를 NOT_FOUND 로 끝내는 등 Check 자체가 실패한 경우.
        response.status_code = _GRPC_TO_HTTP.get(exc.code(), 500)
        return GrpcHealthResponse(service=service, status="SERVICE_UNKNOWN")

    name, http_status = _STATUS_TO_HTTP.get(status_value, ("UNKNOWN", 503))
    response.status_code = http_status
    return GrpcHealthResponse(service=service, status=name)
