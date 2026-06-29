"""게이트웨이 뷰.

REST 엔드포인트를 노출하고 내부에서 gRPC 백엔드의 오래 걸리는 작업을 호출한다.
호출마다 per-call 데드라인(timeout)을 적용하고, gRPC 상태코드를 HTTP 로 매핑한다.
데드라인 초과 시 DEADLINE_EXCEEDED → 504.
"""

import json
import time

import grpc
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from gateway.grpc_client import get_client

_GRPC_TO_HTTP = {
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,  # 데드라인 초과(작업 취소됨)
    grpc.StatusCode.CANCELLED: 499,          # 취소됨
    grpc.StatusCode.UNAVAILABLE: 503,
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.PERMISSION_DENIED: 403,
    grpc.StatusCode.UNAUTHENTICATED: 401,
}


def health(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_http_methods(["POST"])
def operation(request):
    # 입력 파싱 + 검증
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid JSON"}, status=400)

    data = payload.get("data")
    if not isinstance(data, str) or not data:
        return JsonResponse({"detail": "data는 비어있지 않은 문자열이어야 합니다."}, status=422)

    # deadline_ms 가 없으면 기본값. gRPC timeout 은 초 단위.
    deadline_ms = payload.get("deadline_ms")
    if deadline_ms is None:
        deadline_ms = settings.GRPC_DEFAULT_DEADLINE_MS
    if not isinstance(deadline_ms, int) or deadline_ms <= 0:
        return JsonResponse({"detail": "deadline_ms는 양의 정수여야 합니다."}, status=422)
    timeout_s = deadline_ms / 1000.0

    started = time.perf_counter()
    try:
        result = get_client().long_running_operation(data, timeout=timeout_s)
    except grpc.RpcError as exc:
        status = _GRPC_TO_HTTP.get(exc.code(), 500)
        return JsonResponse({"detail": exc.details()}, status=status)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return JsonResponse({"result": result, "elapsed_ms": elapsed_ms})
