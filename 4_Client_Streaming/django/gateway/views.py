"""게이트웨이 뷰.

REST 엔드포인트를 노출하고 내부에서 gRPC 백엔드를 **클라이언트 스트리밍**으로
호출한다. 요청 본문의 items 리스트를 gRPC 요청 스트림으로 변환해 보내고,
서버가 집계한 단일 응답을 돌려준다. gRPC 상태코드를 HTTP 상태코드로 매핑한다.
"""

import json
import time

import grpc
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
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


@csrf_exempt
@require_http_methods(["POST"])
def stream_data(request):
    # 입력 파싱 + 검증
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid JSON"}, status=400)

    items = payload.get("items")
    # items 는 비어있지 않은 문자열 리스트여야 한다.
    if (
        not isinstance(items, list)
        or len(items) == 0
        or not all(isinstance(i, str) for i in items)
    ):
        return JsonResponse(
            {"detail": "items는 비어있지 않은 문자열 리스트여야 합니다."}, status=422
        )

    started = time.perf_counter()
    try:
        result = get_client().stream_data(items)
    except grpc.RpcError as exc:
        status = _GRPC_TO_HTTP.get(exc.code(), 500)
        return JsonResponse({"detail": exc.details()}, status=status)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return JsonResponse({"result": result, "count": len(items), "elapsed_ms": elapsed_ms})
