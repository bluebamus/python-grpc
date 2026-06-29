"""gRPC 클라이언트 래퍼 (양방향 스트리밍).

이 예제(5_Bidirectional_Streaming)의 핵심은 **양방향 스트림**이다.
`ChatService.Chat` 은 `stream ChatMessage` 를 받아 `stream ChatMessage` 를
돌려준다. 즉 클라이언트가 메시지를 보내는 동안 서버도 동시에 응답을 흘려보낸다.

동기(grpc) 스텁에서 양방향 스트림은 "요청 이터레이터를 넘기면 응답 이터레이터를
돌려받는" 모양이다. 요청 이터레이터를 큐로 구동하면(아래 main.py 참조), 외부에서
도착하는 메시지를 실시간으로 스트림에 밀어 넣을 수 있다.
"""

import grpc

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import messages_pb2  # noqa: F401  (호출 측에서 ChatMessage 생성에 사용)
import messages_pb2_grpc

from app.config import settings


class GrpcClient:
    """게이트웨이 수명 동안 재사용하는 채널/스텁 보관 객체.

    채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
    """

    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._channel: grpc.Channel | None = None
        self._stub: messages_pb2_grpc.ChatServiceStub | None = None

    def connect(self) -> None:
        self._channel = grpc.insecure_channel(self._target)
        self._stub = messages_pb2_grpc.ChatServiceStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    def chat(self, request_iterator):
        """양방향 스트림 호출.

        `request_iterator` 는 `ChatMessage` 를 yield 하는 이터러블이며,
        반환값은 서버가 흘려보내는 `ChatMessage` 응답 이터레이터다.
        요청을 다 보내기 전에도 응답을 받을 수 있다(진짜 양방향).
        """
        if self._stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        return self._stub.Chat(request_iterator)
