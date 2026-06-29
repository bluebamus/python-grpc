"""게이트웨이 뷰.

REST 엔드포인트를 노출하고 내부에서 gRPC 백엔드를 호출한다.
호출 경로에는 클라이언트 인터셉터가 끼어 있어 로깅과 x-request-id 주입을
자동으로 처리한다. gRPC 상태코드를 HTTP 상태코드로 매핑한다.
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
def echo(request):
    # 입력 파싱 + 검증
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid JSON"}, status=400)
    message = payload.get("message")
    if not isinstance(message, str) or not message:
        return JsonResponse({"detail": "message는 비어있지 않은 문자열이어야 합니다."}, status=422)

    started = time.perf_counter()
    try:
        result, request_id = get_client().echo(message)
    except grpc.RpcError as exc:
        status = _GRPC_TO_HTTP.get(exc.code(), 500)
        return JsonResponse({"detail": exc.details()}, status=status)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return JsonResponse({"message": result, "request_id": request_id, "elapsed_ms": elapsed_ms})
