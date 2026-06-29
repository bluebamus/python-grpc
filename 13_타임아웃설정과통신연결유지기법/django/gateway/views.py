"""게이트웨이 뷰.

REST 엔드포인트를 노출하고 내부에서 gRPC 백엔드를 호출한다.
호출에는 per-call deadline 을 적용하며, 백엔드가 데드라인 안에 응답하지 못하면
gRPC 가 DEADLINE_EXCEEDED 를 던지고 뷰는 이를 HTTP 504 로 매핑한다.
"""

import json
import time

import grpc
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from gateway.grpc_client import get_client

_GRPC_TO_HTTP = {
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,  # 데드라인 초과 → Gateway Timeout
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
def echo(request):
    # 입력 파싱 + 검증
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid JSON"}, status=400)
    message = payload.get("message")
    if not isinstance(message, str) or not message:
        return JsonResponse({"detail": "message는 비어있지 않은 문자열이어야 합니다."}, status=422)

    # deadline_ms 는 선택. 주면 양의 정수여야 한다.
    deadline_ms = payload.get("deadline_ms")
    if deadline_ms is not None and (not isinstance(deadline_ms, int) or deadline_ms < 1):
        return JsonResponse({"detail": "deadline_ms는 1 이상의 정수여야 합니다."}, status=422)

    started = time.perf_counter()
    try:
        result = get_client().echo(message, deadline_ms=deadline_ms)
    except grpc.RpcError as exc:
        status = _GRPC_TO_HTTP.get(exc.code(), 500)
        return JsonResponse({"detail": exc.details()}, status=status)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return JsonResponse({"message": result, "elapsed_ms": elapsed_ms})
