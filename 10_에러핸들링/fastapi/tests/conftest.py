"""통합 테스트용 픽스처.

실제 gRPC 서버를 백그라운드로 띄우고, FastAPI 게이트웨이가 그 서버를
호출하도록 한다. 에러 핸들링(gRPC StatusCode -> HTTP 매핑)을 결정론적으로
검증하기 위해, 입력에 따라 정해진 상태코드로 abort 하는 서비서를 직접 작성한다.

상위 폴더의 server.py 는 import()/print 등이 섞여 있어 테스트에 부적합하므로
여기서 결정론적 서비서를 따로 만든다.
"""

from concurrent import futures

import grpc
import pytest

# proto 경로 등록 후 생성 코드 import
from app import proto  # noqa: F401
import error_handling_example_pb2 as pb2
import error_handling_example_pb2_grpc as pb2_grpc

# 이 예제에 배정된 고유 포트 (포트 충돌 방지)
GRPC_PORT = 50060
GRPC_TARGET = f"localhost:{GRPC_PORT}"


class CalculatorServicer(pb2_grpc.CalculatorServicer):
    """결정론적 계산기 서비서.

    - divisor == 0      -> INVALID_ARGUMENT  (게이트웨이가 HTTP 400 으로 매핑)
    - dividend < 0      -> PERMISSION_DENIED (게이트웨이가 HTTP 403 으로 매핑)
                           * 매핑 표 검증용으로 일부러 둔 데모 규칙
    - 그 외             -> 정상 몫 반환
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
    """세션 동안 결정론적 gRPC 서버를 한 번 띄우고, 끝나면 정리한다."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    pb2_grpc.add_CalculatorServicer_to_server(CalculatorServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    yield server
    server.stop(grace=None)
