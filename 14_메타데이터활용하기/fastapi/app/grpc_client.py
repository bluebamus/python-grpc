"""gRPC 클라이언트 래퍼.

이 예제(14_메타데이터활용하기)의 핵심은 **HTTP 헤더를 gRPC 메타데이터로
변환해 주입**하고, 서버가 돌려준 메타데이터를 다시 읽어 HTTP 응답으로
노출하는 것이다.

- 메타데이터는 `(키, 값)` 튜플의 시퀀스다. 키는 소문자여야 하며(gRPC 규약),
  HTTP 헤더 `Authorization` / `X-Request-Id` 는 각각 `authorization` /
  `x-request-id` 로 매핑한다.
- 응답 메타데이터는 `stub.Echo.with_call(...)` 가 돌려주는 call 객체의
  `trailing_metadata()` 로 읽는다.
"""

import grpc

from app.config import settings

# proto 패키지를 먼저 import 해서 sys.path 에 컴파일된 코드 경로를 등록한다.
from app import proto  # noqa: F401
import metadata_example_pb2
import metadata_example_pb2_grpc


class EchoResult:
    """게이트웨이가 서버로부터 받은 결과 묶음.

    message      : Echo 응답 메시지
    request_id   : 서버가 trailing metadata 로 되돌려준 x-request-id
    auth_present : 서버가 본 Authorization 메타데이터의 존재 여부("true"/"false")
    """

    def __init__(self, message: str, request_id: str, auth_present: str) -> None:
        self.message = message
        self.request_id = request_id
        self.auth_present = auth_present


class GrpcClient:
    """게이트웨이 수명 동안 재사용하는 채널/스텁 보관 객체.

    채널은 비싸므로 요청마다 새로 만들지 않고 한 번 만들어 재사용한다.
    """

    def __init__(self, target: str | None = None) -> None:
        self._target = target or settings.grpc_target
        self._channel: grpc.Channel | None = None
        self._stub: metadata_example_pb2_grpc.EchoServiceStub | None = None

    def connect(self) -> None:
        self._channel = grpc.insecure_channel(self._target)
        self._stub = metadata_example_pb2_grpc.EchoServiceStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    def echo(
        self,
        message: str,
        request_id: str,
        authorization: str | None = None,
        timeout: float | None = None,
    ) -> EchoResult:
        """Echo 호출. HTTP 헤더에서 온 값을 gRPC 메타데이터로 주입한다.

        request_id 는 게이트웨이가 보장(없으면 생성)하므로 항상 채운다.
        authorization 은 클라이언트가 보냈을 때만 주입한다(누락 케이스 검증용).
        """
        if self._stub is None:
            raise RuntimeError("GrpcClient.connect() 가 먼저 호출되어야 합니다.")

        # --- HTTP 헤더 -> gRPC 메타데이터 변환 ---
        metadata: list[tuple[str, str]] = [("x-request-id", request_id)]
        if authorization:
            metadata.append(("authorization", authorization))

        request = metadata_example_pb2.EchoRequest(message=message)
        response, call = self._stub.Echo.with_call(
            request,
            metadata=tuple(metadata),
            timeout=timeout if timeout is not None else settings.grpc_timeout,
        )

        # --- 서버가 보낸 trailing 메타데이터 읽기 ---
        trailing = dict(call.trailing_metadata())
        # 서버가 x-request-id 를 그대로 되돌려준다(왕복 증명). 없으면 보낸 값 유지.
        returned_request_id = trailing.get("x-request-id", request_id)
        auth_present = trailing.get("x-auth-present", "false")

        return EchoResult(
            message=response.message,
            request_id=returned_request_id,
            auth_present=auth_present,
        )
