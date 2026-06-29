"""게이트웨이 뷰.

REST 엔드포인트를 노출하고 내부에서 gzip 압축 채널로 gRPC 백엔드를 호출한다.
받은 bytes 는 base64 로 인코딩해 JSON 으로 응답하고, gRPC 상태코드는
HTTP 상태코드로 매핑한다.
"""

import base64
import time

import grpc
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from gateway.grpc_client import get_client

_GRPC_TO_HTTP = {
    grpc.StatusCode.UNAVAILABLE: 503,
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.PERMISSION_DENIED: 403,
    grpc.StatusCode.UNAUTHENTICATED: 401,
}


def health(request):
    return JsonResponse({"status": "ok"})


@require_http_methods(["GET"])
def get_data(request, data_id: str):
    started = time.perf_counter()
    try:
        data = get_client().get_data(data_id)
    except grpc.RpcError as exc:
        status = _GRPC_TO_HTTP.get(exc.code(), 500)
        return JsonResponse({"detail": exc.details()}, status=status)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    # bytes 는 JSON 으로 직접 실을 수 없으므로 base64 로 인코딩한다.
    return JsonResponse(
        {
            "data_id": data_id,
            "data_base64": base64.b64encode(data).decode("ascii"),
            "size": len(data),
            "elapsed_ms": elapsed_ms,
        }
    )
