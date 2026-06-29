"""통합 테스트용 픽스처.

실제 gRPC 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 그 서버를
호출하도록 한다. 압축 검증을 결정론적으로 하기 위해, data_id 로부터 고정된
큰 바이트 페이로드를 만들어 반환하는 서비서를 사용한다. (압축은 전송 계층에서
일어나므로, 알고리즘이 무엇이든 복원된 바이트는 동일해야 한다.)
"""

from concurrent import futures

import grpc
import pytest

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import example_pb2
import example_pb2_grpc

# 이 예제(8_데이터압축기법)에 배정된 고유 포트.
GRPC_PORT = 50058
GRPC_TARGET = f"localhost:{GRPC_PORT}"


def make_payload(data_id: str) -> bytes:
    """data_id 로부터 결정론적으로 만들어지는 큰(압축 효과가 있는) 페이로드."""
    # 반복 패턴이라 압축률이 높다. 알고리즘별로도 동일한 원본이 복원돼야 한다.
    return (f"data-{data_id}:".encode() + b"COMPRESS-ME-" * 10000)


class DataServicer(example_pb2_grpc.DataServiceServicer):
    """data_id 에 대해 결정론적 큰 바이트를 반환한다.

    서버는 모든 압축 알고리즘을 받아들이도록 압축 옵션 없이 생성한다(서버는
    클라이언트가 보낸 인코딩을 자동 해석하고, 응답도 클라이언트가 수용 가능한
    알고리즘으로 압축한다).
    """

    def GetData(self, request, context):
        return example_pb2.DataResponse(data=make_payload(request.data_id))


def _start_server(servicer) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    example_pb2_grpc.add_DataServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    return server


@pytest.fixture
def grpc_server():
    """테스트용 gRPC 서버를 띄우고, 종료 시 정리한다."""
    server = _start_server(DataServicer())
    yield server
    server.stop(grace=None)
