"""gRPC 클라이언트 래퍼.

이 예제(6_요청취소기법)의 핵심은 호출마다 **데드라인(timeout)** 을 적용하고,
필요하면 진행 중인 호출을 **취소(cancel)** 하는 것이다.

- 데드라인을 넘기면 gRPC 런타임이 `DEADLINE_EXCEEDED` 를 발생시키고, 서버 측
  context 가 비활성화되어 백엔드 작업도 중단된다.
- 클라이언트(브라우저)가 연결을 끊으면 게이트웨이는 future.cancel() 로 호출을
  취소해 백엔드 자원이 낭비되지 않게 한다.
"""

import grpc

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import cancel_example_pb2
import cancel_example_pb2_grpc

from app.config import settings


class GrpcClient:
    """게이트웨이 수명 동안 재사용하는 채널/스텁 보관 객체.

    채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
    """

    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._channel: grpc.Channel | None = None
        self._stub: cancel_example_pb2_grpc.CancelServiceStub | None = None

    def connect(self) -> None:
        self._channel = grpc.insecure_channel(self._target)
        self._stub = cancel_example_pb2_grpc.CancelServiceStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    def start_operation(self, data: str, timeout: float):
        """LongRunningOperation 을 비동기 future 로 시작한다.

        future 를 그대로 돌려주므로, 호출 측에서 `future.done()` 으로 완료 여부를
        폴링하고 `future.cancel()` 로 취소할 수 있다. `timeout` 은 per-call
        데드라인이며, 초과 시 future 가 `DEADLINE_EXCEEDED` 로 종료된다.
        """
        if self._stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        request = cancel_example_pb2.Request(request_data=data)
        return self._stub.LongRunningOperation.future(request, timeout=timeout)
