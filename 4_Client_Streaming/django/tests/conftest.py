"""Django 통합 테스트용 픽스처.

FastAPI 샘플과 동일하게, 클라이언트 스트리밍 집계를 결정론적으로 검증하기
위해 요청 스트림으로 받은 아이템들을 모아 개수/연결 문자열을 result 로
돌려주는 gRPC 서버를 백그라운드로 띄운다.
"""

from concurrent import futures

import grpc
import pytest

from gateway import proto  # noqa: F401
import streaming_pb2
import streaming_pb2_grpc
from gateway import grpc_client

GRPC_PORT = 50054


class AggregatingServicer(streaming_pb2_grpc.StreamingServiceServicer):
    """요청 스트림의 모든 data 를 모아 `count=N;data=a|b|c` 로 집계한다."""

    def StreamData(self, request_iterator, context):
        items = [req.data for req in request_iterator]
        result = f"count={len(items)};data=" + "|".join(items)
        return streaming_pb2.ResponseMessage(result=result)


@pytest.fixture
def grpc_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    streaming_pb2_grpc.add_StreamingServiceServicer_to_server(AggregatingServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()

    # 각 테스트마다 채널을 새로 만들어 이전 서버 연결 상태가 새지 않게 한다.
    grpc_client.reset_client()
    yield
    grpc_client.reset_client()
    server.stop(grace=None)
