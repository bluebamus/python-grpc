"""gRPC 클라이언트 래퍼 (Django).

FastAPI 샘플과 동일한 원리: 채널/호출에 gzip 압축을 적용한다.
큰 바이너리 응답(bytes)을 적은 네트워크 비용으로 받기 위함이다.
채널은 비싸므로 모듈 레벨에서 한 번 만들어 재사용한다(get_client).
설정값은 Django settings 에서 읽는다.
"""

import grpc
from django.conf import settings

from gateway import proto  # noqa: F401  (sys.path 등록)
import example_pb2
import example_pb2_grpc


def _compression() -> grpc.Compression:
    """settings 의 문자열을 grpc.Compression 으로 변환한다."""
    return {
        "Gzip": grpc.Compression.Gzip,
        "Deflate": grpc.Compression.Deflate,
        "NoCompression": grpc.Compression.NoCompression,
    }.get(settings.GRPC_COMPRESSION, grpc.Compression.Gzip)


class GrpcClient:
    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.GRPC_TARGET
        # 채널 단위로 압축을 켠다. 이후 모든 호출에 기본 적용된다.
        self._channel = grpc.insecure_channel(
            self._target, compression=_compression()
        )
        self._stub = example_pb2_grpc.DataServiceStub(self._channel)

    def get_data(self, data_id: str, timeout: float = 5.0) -> bytes:
        request = example_pb2.DataRequest(data_id=data_id)
        # 호출 시에도 압축을 명시(채널 기본값과 동일하게 한 번 더 지정).
        response = self._stub.GetData(
            request, timeout=timeout, compression=_compression()
        )
        return response.data


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
