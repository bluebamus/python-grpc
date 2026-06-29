"""통합 테스트용 픽스처.

실제 TLS gRPC 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 그 서버를
보안 채널로 호출하도록 한다. 서버는 상위 폴더(16_TLS보안/)의 기존 자체서명
인증서(server.key/server.crt)로 `add_secure_port` 한다. 즉 insecure 포트는
전혀 열지 않으므로, 게이트웨이가 정상 응답을 받으면 그것은 TLS 연결이
성공했다는 증거다.
"""

from concurrent import futures
from pathlib import Path

import grpc
import pytest

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import example_pb2
import example_pb2_grpc

# 배정 포트(이 예제 전용). config 기본 target 과 동일해야 한다.
GRPC_PORT = 50066

# 상위 폴더의 기존 자체서명 인증서 위치.
#   tests/conftest.py -> parents[0]=tests, [1]=fastapi, [2]=16_TLS보안
_CERT_DIR = Path(__file__).resolve().parents[2]


class HelloServicer(example_pb2_grpc.ExampleServiceServicer):
    """결정론적으로 동작하는 테스트 서비서."""

    def SayHello(self, request, context):
        return example_pb2.HelloReply(message=f"Hello, {request.name}!")


def _server_credentials() -> grpc.ServerCredentials:
    with open(_CERT_DIR / "server.key", "rb") as f:
        private_key = f.read()
    with open(_CERT_DIR / "server.crt", "rb") as f:
        certificate_chain = f.read()
    return grpc.ssl_server_credentials(((private_key, certificate_chain),))


@pytest.fixture
def tls_grpc_server():
    """TLS 보안 포트만 여는 테스트 gRPC 서버. 종료 시 정리."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    example_pb2_grpc.add_ExampleServiceServicer_to_server(HelloServicer(), server)
    # insecure 가 아니라 secure 포트로만 바인딩한다.
    server.add_secure_port(f"[::]:{GRPC_PORT}", _server_credentials())
    server.start()
    yield server
    server.stop(grace=None)
