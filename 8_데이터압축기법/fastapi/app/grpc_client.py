"""gRPC 클라이언트 래퍼.

이 예제(8_데이터압축기법)의 핵심은 두 가지 압축 적용 지점을 보여주는 것이다.

1. 채널 단위(channel-level) 기본 압축: 채널을 만들 때 `compression=` 으로
   지정하면, 그 채널의 모든 호출이 기본으로 그 알고리즘을 사용한다.
2. 호출 단위(per-call) 압축 오버라이드: 개별 RPC 호출 시 `compression=` 을
   넘기면 채널 기본값을 덮어쓴다. 호출마다 다른 알고리즘을 쓸 수 있다.

압축은 전송 계층(transport)에서 일어난다. 즉 알고리즘이 무엇이든 수신 측이
복원한 바이트는 동일하다. 압축은 "전송량"을 줄일 뿐 "데이터 내용"은 바꾸지 않는다.
"""

import grpc

from app.config import settings

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import example_pb2
import example_pb2_grpc

# 압축 알고리즘 이름 -> grpc.Compression 매핑.
# 설정/쿼리스트링에서 받은 문자열을 gRPC 런타임 enum 으로 변환한다.
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
    """게이트웨이 수명 동안 재사용하는 채널/스텁 보관 객체.

    채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
    채널 생성 시 기본 압축 알고리즘을 주입한다.
    """

    def __init__(self, target: str | None = None, default_compression: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._default_compression = default_compression or settings.default_compression
        self._channel: grpc.Channel | None = None
        self._stub: example_pb2_grpc.DataServiceStub | None = None

    def connect(self) -> None:
        # 채널 단위 기본 압축을 주입한다. 호출 시 오버라이드하지 않으면 이 값이 적용된다.
        default = resolve_compression(self._default_compression)
        self._channel = grpc.insecure_channel(self._target, compression=default)
        self._stub = example_pb2_grpc.DataServiceStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    def get_data(
        self,
        data_id: str,
        compression: str | None = None,
        timeout: float = 5.0,
    ) -> bytes:
        """GetData 호출. compression 을 주면 호출 단위로 채널 기본값을 오버라이드한다.

        compression=None 이면 채널 기본 압축(connect 시 주입)이 그대로 쓰인다.
        반환되는 bytes 는 압축 알고리즘과 무관하게 동일하다(전송 계층 압축).
        """
        if self._stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        request = example_pb2.DataRequest(data_id=data_id)
        call_kwargs: dict[str, object] = {"timeout": timeout}
        if compression is not None:
            # 호출 단위 압축 오버라이드.
            call_kwargs["compression"] = resolve_compression(compression)
        response = self._stub.GetData(request, **call_kwargs)
        return response.data
