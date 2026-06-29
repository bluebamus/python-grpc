"""gRPC 클라이언트 래퍼.

이 예제(3_ServerStreaming)의 핵심은 서버 스트리밍 RPC 다.
요청 1개를 보내면 서버가 응답을 여러 개 stream 으로 흘려보낸다.
게이트웨이는 이 gRPC 스트림을 그대로 받아 HTTP 스트리밍(SSE)으로 클라이언트에
중계한다. 응답을 한 번에 모아서 주는 게 아니라, 도착하는 대로 흘려보낸다는
점이 포인트다.
"""

from collections.abc import Iterator

import grpc

from app.config import settings

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import message_pb2
import message_pb2_grpc


class GrpcClient:
    """게이트웨이 수명 동안 재사용하는 채널/스텁 보관 객체.

    채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
    """

    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._channel: grpc.Channel | None = None
        self._stub: message_pb2_grpc.ChatServiceStub | None = None

    def connect(self) -> None:
        self._channel = grpc.insecure_channel(self._target)
        self._stub = message_pb2_grpc.ChatServiceStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    def chat_stream(
        self, message: str, timeout: float | None = None
    ) -> Iterator[str]:
        """ChatStream 호출. 요청 1개 → 응답 스트림.

        gRPC 응답 스트림을 순회하며 각 메시지의 문자열만 yield 한다.
        제너레이터이므로 게이트웨이는 서버가 보내는 대로 하나씩 받아 흘려보낼 수 있다.
        timeout 은 스트림 전체에 대한 데드라인이다.
        """
        if self._stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        request = message_pb2.ChatMessage(message=message)
        call = self._stub.ChatStream(
            request, timeout=timeout if timeout is not None else settings.stream_timeout
        )
        for response in call:
            yield response.message
