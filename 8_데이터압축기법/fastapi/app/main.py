"""FastAPI 게이트웨이 앱.

REST 엔드포인트(GET /data/{data_id})를 노출하고, 내부적으로 gRPC 백엔드를
호출한다. 쿼리스트링 `compression` 으로 호출 단위 압축 알고리즘을 선택할 수
있다. gRPC 상태코드를 HTTP 상태코드로 매핑해 외부에는 표준 HTTP 의미로 응답한다.
"""

import base64
import time
from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, HTTPException, Query

from app.config import settings
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
    # 앱 기동 시 채널을 한 번 열고, 종료 시 닫는다. 채널에는 기본 압축이 주입된다.
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
def get_data(
    data_id: str,
    # compression 미지정 시 채널 기본 압축이 쓰인다. 지정 시 호출 단위 오버라이드.
    compression: str | None = Query(
        default=None,
        description="압축 알고리즘: none | deflate | gzip (미지정 시 채널 기본값)",
    ),
) -> DataResponse:
    client: GrpcClient = app.state.grpc
    # 응답에 표기할 '실제 적용된' 압축 알고리즘. 미지정이면 채널 기본값.
    applied = (compression or settings.default_compression).lower()
    started = time.perf_counter()
    try:
        data = client.get_data(data_id, compression=compression)
    except ValueError as exc:
        # 알 수 없는 압축 알고리즘 이름 -> 잘못된 요청
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except grpc.RpcError as exc:
        http_status = _GRPC_TO_HTTP.get(exc.code(), 500)
        raise HTTPException(status_code=http_status, detail=exc.details()) from exc
    elapsed_ms = (time.perf_counter() - started) * 1000
    return DataResponse(
        data_id=data_id,
        data_base64=base64.b64encode(data).decode("ascii"),
        size=len(data),
        compression=applied,
        elapsed_ms=round(elapsed_ms, 2),
    )
