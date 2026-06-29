"""Django 통합 테스트용 픽스처.

FastAPI 샘플과 동일하게, 압축 동작을 결정론적으로 검증하기 위해 data_id 에
대해 크고 반복적인(=잘 압축되는) bytes 를 돌려주는 gRPC 서버를 띄운다.
"""

from concurrent import futures

import grpc
import pytest

from gateway import proto  # noqa: F401
import example_pb2
import example_pb2_grpc
from gateway import grpc_client

# 7_데이터압축하기 예제에 배정된 고유 포트
GRPC_PORT = 50057

PAYLOAD_SIZE = 10000
KNOWN_ID = "1"


class DataServicer(example_pb2_grpc.DataServiceServicer):
    """KNOWN_ID 면 b"X" * PAYLOAD_SIZE, 그 외 id 는 NOT_FOUND."""

    def GetData(self, request, context):
        if request.data_id != KNOWN_ID:
            context.abort(grpc.StatusCode.NOT_FOUND, f"no data for id={request.data_id}")
        return example_pb2.DataResponse(data=b"X" * PAYLOAD_SIZE)


@pytest.fixture
def grpc_server():
    # 서버 쪽도 gzip 압축을 켜 둔다(클라이언트가 압축을 요청하면 그대로 응답).
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=4),
        compression=grpc.Compression.Gzip,
    )
    example_pb2_grpc.add_DataServiceServicer_to_server(DataServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()

    # 각 테스트마다 채널을 새로 만들어 이전 상태가 새지 않게 한다.
    grpc_client.reset_client()
    yield server
    grpc_client.reset_client()

    server.stop(grace=None)
