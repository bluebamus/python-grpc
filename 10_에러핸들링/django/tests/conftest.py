"""Django 통합 테스트용 픽스처.

FastAPI 샘플과 동일하게, 결정론적 에러 매핑 검증을 위해 입력에 따라 정해진
상태코드로 abort 하는 gRPC 서버를 백그라운드로 띄운다.
상위 폴더의 server.py 는 테스트에 부적합하므로 여기서 직접 작성한다.
"""

from concurrent import futures

import grpc
import pytest

from gateway import proto  # noqa: F401
import error_handling_example_pb2 as pb2
import error_handling_example_pb2_grpc as pb2_grpc
from gateway import grpc_client

# 이 예제에 배정된 고유 포트 (포트 충돌 방지)
GRPC_PORT = 50060


class CalculatorServicer(pb2_grpc.CalculatorServicer):
    """결정론적 계산기 서비서.

    - divisor == 0  -> INVALID_ARGUMENT  (뷰가 HTTP 400 으로 매핑)
    - dividend < 0  -> PERMISSION_DENIED (뷰가 HTTP 403 으로 매핑, 매핑 표 검증용)
    - 그 외         -> 정상 몫 반환
    """

    def Divide(self, request, context):
        if request.divisor == 0:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Division by zero is not allowed.",
            )
        if request.dividend < 0:
            context.abort(
                grpc.StatusCode.PERMISSION_DENIED,
                "Negative dividend is not permitted in this demo.",
            )
        return pb2.DivideResponse(quotient=request.dividend / request.divisor)


@pytest.fixture(scope="session", autouse=True)
def grpc_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    pb2_grpc.add_CalculatorServicer_to_server(CalculatorServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    # 채널을 새로 만들어 이전 상태가 새지 않게 한다.
    grpc_client.reset_client()
    yield server
    grpc_client.reset_client()
    server.stop(grace=None)
