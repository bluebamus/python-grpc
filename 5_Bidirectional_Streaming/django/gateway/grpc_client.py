"""gRPC 클라이언트 래퍼 (Django, 양방향 스트리밍 → 반이중 배치).

이 예제의 ChatService 는 양방향 스트리밍이지만, Django(WSGI)는 진정한
양방향/WebSocket 에 부적합하다(아래 한계 참조). 그래서 실무적 대안으로
**반이중 배치**를 제공한다: messages 리스트를 한 번에 bidi 스트림으로 보내고,
서버가 돌려준 응답들을 모두 모아 리스트로 반환한다.

채널은 비싸므로 모듈 레벨에서 한 번 만들어 재사용한다(get_client).
"""

import grpc
from django.conf import settings

from gateway import proto  # noqa: F401  (sys.path 등록)
import messages_pb2
import messages_pb2_grpc


class GrpcClient:
    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.GRPC_TARGET
        self._channel = grpc.insecure_channel(self._target)
        self._stub = messages_pb2_grpc.ChatServiceStub(self._channel)

    def chat_batch(self, messages: list[str], timeout: float = 5.0) -> list[str]:
        """messages 를 bidi 스트림으로 보내고 응답들을 모아 반환(반이중 배치).

        요청을 모두 보낸 뒤 응답을 모으는 형태라 '반이중'이다. 진짜 양방향처럼
        보내는 도중 응답을 처리하지는 않지만, 양방향 RPC 를 그대로 사용한다.
        """

        def request_gen():
            for msg in messages:
                yield messages_pb2.ChatMessage(message=msg)

        responses = self._stub.Chat(request_gen(), timeout=timeout)
        return [response.message for response in responses]


_client: GrpcClient | None = None


def get_client() -> GrpcClient:
    """프로세스 단위로 재사용되는 클라이언트를 반환한다."""
    global _client
    if _client is None:
        _client = GrpcClient()
    return _client


def reset_client() -> None:
    """테스트에서 채널을 다시 만들고 싶을 때 사용."""
    global _client
    _client = None
