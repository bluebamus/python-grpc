"""gRPC 클라이언트 래퍼.

이 예제(7_데이터압축하기)의 핵심은 채널/호출에 gzip 압축을 적용하는 것이다.
바이트가 큰 응답(예: 이미지, 직렬화된 모델, 대용량 JSON)을 주고받을 때
압축을 켜면 네트워크로 흐르는 바이트 수가 크게 줄어든다. 압축/해제는
gRPC 런타임이 투명하게 처리하므로 애플리케이션 코드는 일반 호출과 동일하다.
"""

import grpc

from app.config import settings

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import example_pb2
import example_pb2_grpc


def _compression() -> grpc.Compression:
    """설정 문자열을 grpc.Compression 으로 변환한다.

    Gzip / Deflate / NoCompression 을 지원한다.
    """
    return {
        "Gzip": grpc.Compression.Gzip,
        "Deflate": grpc.Compression.Deflate,
        "NoCompression": grpc.Compression.NoCompression,
    }.get(settings.grpc_compression, grpc.Compression.Gzip)


class GrpcClient:
    """게이트웨이 수명 동안 재사용하는 채널/스텁 보관 객체.

    채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
    채널 생성 시 compression 을 지정하면 이 채널의 모든 호출에 기본 적용된다.
    """

    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._channel: grpc.Channel | None = None
        self._stub: example_pb2_grpc.DataServiceStub | None = None

    def connect(self) -> None:
        # 채널 단위로 압축을 켠다. 이후 모든 호출에 gzip 이 기본 적용된다.
        self._channel = grpc.insecure_channel(
            self._target, compression=_compression()
        )
        self._stub = example_pb2_grpc.DataServiceStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    def get_data(self, data_id: str, timeout: float = 5.0) -> bytes:
        """GetData 호출. 응답 bytes 를 그대로 반환한다.

        호출 시에도 compression 을 명시해 채널 기본값을 덮어쓸 수 있다.
        여기서는 채널 압축과 동일하게 명시적으로 한 번 더 지정해 둔다.
        """
        if self._stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")
        request = example_pb2.DataRequest(data_id=data_id)
        response = self._stub.GetData(
            request, timeout=timeout, compression=_compression()
        )
        return response.data
