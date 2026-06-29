"""통합 테스트용 픽스처.

실제 gRPC 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 그 서버를
호출하도록 한다. 클라이언트 스트리밍 집계를 결정론적으로 검증하기 위해,
요청 스트림으로 받은 아이템들을 모아 개수와 연결 문자열을 result 로
돌려주는 서비서를 사용한다.
"""

from concurrent import futures

import grpc
import pytest

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import streaming_pb2
import streaming_pb2_grpc

GRPC_PORT = 50054
GRPC_TARGET = f"localhost:{GRPC_PORT}"


class AggregatingServicer(streaming_pb2_grpc.StreamingServiceServicer):
    """클라이언트 스트리밍 서비서.

    요청 스트림으로 들어온 모든 RequestMessage.data 를 모아,
    `count=<개수>;data=<a|b|c>` 형태의 단일 result 로 집계해 반환한다.
    결정론적이므로 테스트에서 정확한 문자열을 단언할 수 있다.
    """

    def StreamData(self, request_iterator, context):
        items = [req.data for req in request_iterator]
        result = f"count={len(items)};data=" + "|".join(items)
        return streaming_pb2.ResponseMessage(result=result)


def _start_server(servicer) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    streaming_pb2_grpc.add_StreamingServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    return server


@pytest.fixture
def grpc_server():
    """집계 서비서를 띄우고, 테스트 종료 시 정리한다."""
    servicer = AggregatingServicer()
    server = _start_server(servicer)
    yield servicer
    server.stop(grace=None)
