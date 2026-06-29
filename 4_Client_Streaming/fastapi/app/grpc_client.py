"""gRPC 클라이언트 래퍼.

이 예제(4_Client_Streaming)의 핵심은 **클라이언트 스트리밍**이다.
게이트웨이가 받은 여러 개의 아이템을 gRPC 요청 스트림으로 변환해
StreamData 를 호출하고, 서버가 집계한 단일 ResponseMessage 를 받는다.

요청 스트림은 제너레이터로 만든다. stub.StreamData(<iterator>) 형태로
RequestMessage 를 하나씩 yield 하면 gRPC 런타임이 차례로 전송한다.
"""

from collections.abc import Iterator, Sequence

import grpc

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import streaming_pb2
import streaming_pb2_grpc

from app.config import settings


class GrpcClient:
    """게이트웨이 수명 동안 재사용하는 채널/스텁 보관 객체.

    채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
    """

    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._channel: grpc.Channel | None = None
        self._stub: streaming_pb2_grpc.StreamingServiceStub | None = None

    def connect(self) -> None:
        self._channel = grpc.insecure_channel(self._target)
        self._stub = streaming_pb2_grpc.StreamingServiceStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    @staticmethod
    def _request_iterator(items: Sequence[str]) -> Iterator[streaming_pb2.RequestMessage]:
        """각 아이템을 RequestMessage 로 yield 하는 요청 스트림 제너레이터."""
        for item in items:
            yield streaming_pb2.RequestMessage(data=item)

    def stream_data(self, items: Sequence[str], timeout: float = 5.0) -> str:
        """클라이언트 스트리밍 호출.

        items 를 요청 스트림으로 보내고, 서버가 집계한 단일 결과를 받는다.
        """
        if self._stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        response = self._stub.StreamData(self._request_iterator(items), timeout=timeout)
        return response.result
