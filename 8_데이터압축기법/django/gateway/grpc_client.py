"""gRPC 클라이언트 래퍼 (Django).

FastAPI 샘플과 동일한 원리:
1. 채널 단위(channel-level) 기본 압축을 채널 생성 시 주입한다.
2. 호출 단위(per-call) 압축은 GetData 호출 시 `compression=` 으로 오버라이드한다.

채널은 비싸므로 모듈 레벨에서 한 번 만들어 재사용한다(get_client).
설정값(기본 압축 알고리즘 등)은 Django settings 에서 읽는다.
"""

import grpc
from django.conf import settings

from gateway import proto  # noqa: F401  (sys.path 등록)
import example_pb2
import example_pb2_grpc

# 압축 알고리즘 이름 -> grpc.Compression 매핑.
COMPRESSION_MAP: dict[str, grpc.Compression] = {
    "none": grpc.Compression.NoCompression,
    "deflate": grpc.Compression.Deflate,
    "gzip": grpc.Compression.Gzip,
}


def resolve_compression(name: str) -> grpc.Compression:
    """압축 알고리즘 이름을 grpc.Compression enum 으로 변환한다.

    알 수 없는 이름이면 ValueError 를 던진다(상위에서 400 으로 매핑).
    """
    key = (name or "").lower()
    if key not in COMPRESSION_MAP:
        allowed = ", ".join(COMPRESSION_MAP)
        raise ValueError(f"지원하지 않는 압축 알고리즘: {name!r} (가능: {allowed})")
    return COMPRESSION_MAP[key]


class GrpcClient:
    def __init__(self, target: str | None = None, default_compression: str | None = None) -> None:
        self._target = target or settings.GRPC_TARGET
        default_name = default_compression or settings.GRPC_DEFAULT_COMPRESSION
        # 채널 단위 기본 압축 주입.
        default = resolve_compression(default_name)
        self._channel = grpc.insecure_channel(self._target, compression=default)
        self._stub = example_pb2_grpc.DataServiceStub(self._channel)

    def get_data(
        self,
        data_id: str,
        compression: str | None = None,
        timeout: float = 5.0,
    ) -> bytes:
        """GetData 호출. compression 을 주면 호출 단위로 채널 기본값을 오버라이드한다."""
        request = example_pb2.DataRequest(data_id=data_id)
        call_kwargs: dict[str, object] = {"timeout": timeout}
        if compression is not None:
            call_kwargs["compression"] = resolve_compression(compression)
        response = self._stub.GetData(request, **call_kwargs)
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
