"""gRPC 클라이언트 래퍼 (Django).

FastAPI 샘플과 동일한 원리: 서버 스트리밍 RPC(ChatStream)를 호출하고,
응답 stream 을 제너레이터로 순회한다(요청 1 → 응답 여러 개).
채널은 비싸므로 모듈 레벨에서 한 번 만들어 재사용한다(get_client).
설정값은 Django settings 에서 읽는다.
"""

from collections.abc import Iterator

import grpc
from django.conf import settings

from gateway import proto  # noqa: F401  (sys.path 등록)
import message_pb2
import message_pb2_grpc


class GrpcClient:
    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.GRPC_TARGET
        self._channel = grpc.insecure_channel(self._target)
        self._stub = message_pb2_grpc.ChatServiceStub(self._channel)

    def chat_stream(self, message: str, timeout: float | None = None) -> Iterator[str]:
        """ChatStream 호출. 요청 1개 → 응답 stream.

        응답이 도착하는 대로 각 메시지 문자열을 yield 한다. 제너레이터이므로
        Django 뷰의 StreamingHttpResponse 가 도착하는 즉시 청크로 흘려보낼 수 있다.
        """
        request = message_pb2.ChatMessage(message=message)
        deadline = timeout if timeout is not None else settings.GRPC_STREAM_TIMEOUT
        call = self._stub.ChatStream(request, timeout=deadline)
        for response in call:
            yield response.message


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
