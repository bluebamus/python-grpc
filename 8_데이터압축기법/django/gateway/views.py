"""게이트웨이 뷰.

REST 엔드포인트를 노출하고 내부에서 gRPC 백엔드를 호출한다.
쿼리스트링 `compression` 으로 호출 단위 압축 알고리즘을 선택한다.
gRPC 상태코드를 HTTP 상태코드로 매핑한다.
"""

import base64
import time

import grpc
from django.conf import settings
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
    # compression 미지정 시 채널 기본 압축이 쓰인다. 지정 시 호출 단위 오버라이드.
    compression = request.GET.get("compression")
    # 응답에 표기할 '실제 적용된' 압축 알고리즘. 미지정이면 채널 기본값.
    applied = (compression or settings.GRPC_DEFAULT_COMPRESSION).lower()

    started = time.perf_counter()
    try:
        data = get_client().get_data(data_id, compression=compression)
    except ValueError as exc:
        # 알 수 없는 압축 알고리즘 이름 -> 잘못된 요청
        return JsonResponse({"detail": str(exc)}, status=400)
    except grpc.RpcError as exc:
        status = _GRPC_TO_HTTP.get(exc.code(), 500)
        return JsonResponse({"detail": exc.details()}, status=status)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return JsonResponse(
        {
            "data_id": data_id,
            "data_base64": base64.b64encode(data).decode("ascii"),
            "size": len(data),
            "compression": applied,
            "elapsed_ms": elapsed_ms,
        }
    )
