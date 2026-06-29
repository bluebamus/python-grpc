"""통합 테스트용 픽스처.

실제 gRPC 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 압축 채널로
그 서버를 호출하도록 한다. 압축 동작을 결정론적으로 검증하기 위해, 서버는
data_id 에 대해 크고 반복적인(=잘 압축되는) bytes 를 돌려준다.
"""

from concurrent import futures

import grpc
import pytest

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import example_pb2
import example_pb2_grpc

# 7_데이터압축하기 예제에 배정된 고유 포트
GRPC_PORT = 50057
GRPC_TARGET = f"localhost:{GRPC_PORT}"

# data_id 하나당 돌려줄 큰 반복 페이로드. 반복 바이트라 gzip 으로 잘 압축된다.
PAYLOAD_SIZE = 10000
KNOWN_ID = "1"


class DataServicer(example_pb2_grpc.DataServiceServicer):
    """결정론적 데이터 서비서.

    KNOWN_ID 면 b"X" * PAYLOAD_SIZE 를 반환하고, 그 외 id 는 NOT_FOUND.
    """

    def GetData(self, request, context):
        if request.data_id != KNOWN_ID:
            context.abort(grpc.StatusCode.NOT_FOUND, f"no data for id={request.data_id}")
        return example_pb2.DataResponse(data=b"X" * PAYLOAD_SIZE)


def _start_server() -> grpc.Server:
    # 서버 쪽도 gzip 압축을 켜 둔다(클라이언트가 압축을 요청하면 그대로 응답).
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=4),
        compression=grpc.Compression.Gzip,
    )
    example_pb2_grpc.add_DataServiceServicer_to_server(DataServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    return server


@pytest.fixture
def grpc_server():
    """테스트용 gRPC 서버를 띄우고 종료 시 정리."""
    server = _start_server()
    yield server
    server.stop(grace=None)
