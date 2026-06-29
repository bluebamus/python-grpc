"""gRPC 클라이언트 래퍼 (Django).

FastAPI 샘플과 동일한 원리: 받은 아이템 리스트를 gRPC **요청 스트림**으로
변환해 StreamData 를 호출하고, 서버가 집계한 단일 응답을 받는다.
채널은 비싸므로 모듈 레벨에서 한 번 만들어 재사용한다(get_client).
설정값은 Django settings 에서 읽는다.
"""

from collections.abc import Iterator, Sequence

import grpc
from django.conf import settings

from gateway import proto  # noqa: F401  (sys.path 등록)
import streaming_pb2
import streaming_pb2_grpc


class GrpcClient:
    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.GRPC_TARGET
        self._channel = grpc.insecure_channel(self._target)
        self._stub = streaming_pb2_grpc.StreamingServiceStub(self._channel)

    @staticmethod
    def _request_iterator(items: Sequence[str]) -> Iterator[streaming_pb2.RequestMessage]:
        """각 아이템을 RequestMessage 로 yield 하는 요청 스트림 제너레이터."""
        for item in items:
            yield streaming_pb2.RequestMessage(data=item)

    def stream_data(self, items: Sequence[str], timeout: float = 5.0) -> str:
        """클라이언트 스트리밍 호출: items 를 요청 스트림으로 보내고 단일 결과 수신."""
        response = self._stub.StreamData(self._request_iterator(items), timeout=timeout)
        return response.result


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
