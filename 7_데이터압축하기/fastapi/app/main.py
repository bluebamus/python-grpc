"""FastAPI 게이트웨이 앱.

REST 엔드포인트(GET /data/{data_id})를 노출하고, 내부적으로 gzip 압축을
적용한 gRPC 채널로 백엔드를 호출한다. 받은 bytes 를 base64 로 인코딩해
JSON 으로 응답한다. gRPC 상태코드는 HTTP 상태코드로 매핑한다.
"""

import base64
import time
from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, HTTPException

from app.grpc_client import GrpcClient
from app.schemas import DataResponse

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
    # 앱 기동 시 압축 채널을 한 번 열고, 종료 시 닫는다.
    client = GrpcClient()
    client.connect()
    app.state.grpc = client
    try:
        yield
    finally:
        client.close()


app = FastAPI(title="gRPC 데이터 압축 게이트웨이", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/data/{data_id}", response_model=DataResponse)
def get_data(data_id: str) -> DataResponse:
    client: GrpcClient = app.state.grpc
    started = time.perf_counter()
    try:
        data = client.get_data(data_id)
    except grpc.RpcError as exc:
        http_status = _GRPC_TO_HTTP.get(exc.code(), 500)
        raise HTTPException(status_code=http_status, detail=exc.details()) from exc
    elapsed_ms = (time.perf_counter() - started) * 1000
    # bytes 는 JSON 으로 직접 실을 수 없으므로 base64 로 인코딩한다.
    return DataResponse(
        data_id=data_id,
        data_base64=base64.b64encode(data).decode("ascii"),
        size=len(data),
        elapsed_ms=round(elapsed_ms, 2),
    )
