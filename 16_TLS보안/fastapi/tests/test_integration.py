"""게이트웨이 통합 테스트.

브라우저 대신 TestClient 로 REST 엔드포인트를 호출하고, 그 호출이 내부
gRPC 백엔드로 'TLS 보안 채널'을 통해 전달되는지 end-to-end 로 확인한다.
"""

import grpc
import pytest
from fastapi.testclient import TestClient

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import example_pb2
import example_pb2_grpc

from app.main import app
from tests.conftest import GRPC_PORT


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_hello_over_tls(tls_grpc_server):
    # 서버는 TLS 포트로만 떠 있고, 게이트웨이는 secure_channel 로 호출한다.
    with TestClient(app) as client:
        resp = client.post("/hello", json={"name": "World"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "Hello, World!"  # TLS 연결이 성공했다는 증거
    assert "elapsed_ms" in body
    assert isinstance(body["elapsed_ms"], (int, float))


def test_insecure_client_is_rejected(tls_grpc_server):
    # 같은 포트에 '평문' 채널로 접속하면 TLS 서버가 핸드셰이크를 거부한다.
    # 이는 서버가 insecure 가 아니라 진짜 TLS 라는 것을 분명히 보여준다.
    channel = grpc.insecure_channel(f"localhost:{GRPC_PORT}")
    stub = example_pb2_grpc.ExampleServiceStub(channel)
    with pytest.raises(grpc.RpcError):
        stub.SayHello(example_pb2.HelloRequest(name="World"), timeout=3.0)
    channel.close()


def test_validation_rejects_empty_name():
    with TestClient(app) as client:
        resp = client.post("/hello", json={"name": ""})
    assert resp.status_code == 422  # Pydantic 검증 실패
