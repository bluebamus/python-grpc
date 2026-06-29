"""Django 통합 테스트용 픽스처.

FastAPI 샘플과 동일하게, 압축 검증을 결정론적으로 하기 위해 data_id 로부터
고정된 큰 바이트 페이로드를 반환하는 gRPC 서버를 백그라운드로 띄운다.
"""

from concurrent import futures

import grpc
import pytest

from gateway import proto  # noqa: F401
import example_pb2
import example_pb2_grpc
from gateway import grpc_client

# 이 예제(8_데이터압축기법)에 배정된 고유 포트.
GRPC_PORT = 50058


def make_payload(data_id: str) -> bytes:
    """data_id 로부터 결정론적으로 만들어지는 큰(압축 효과가 있는) 페이로드."""
    return (f"data-{data_id}:".encode() + b"COMPRESS-ME-" * 10000)


class DataServicer(example_pb2_grpc.DataServiceServicer):
    def GetData(self, request, context):
        return example_pb2.DataResponse(data=make_payload(request.data_id))


@pytest.fixture
def grpc_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    example_pb2_grpc.add_DataServiceServicer_to_server(DataServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()

    # 각 테스트마다 채널을 새로 만들어 이전 상태가 새지 않게 한다.
    grpc_client.reset_client()
    yield server
    grpc_client.reset_client()
    server.stop(grace=None)
