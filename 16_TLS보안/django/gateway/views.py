"""게이트웨이 뷰.

REST 엔드포인트를 노출하고 내부에서 TLS 보안 채널로 gRPC 백엔드를 호출한다.
gRPC 상태코드를 HTTP 상태코드로 매핑한다.
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
def hello(request):
    # 입력 파싱 + 검증
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid JSON"}, status=400)
    name = payload.get("name")
    if not isinstance(name, str) or not name:
        return JsonResponse({"detail": "name은 비어있지 않은 문자열이어야 합니다."}, status=422)

    started = time.perf_counter()
    try:
        result = get_client().say_hello(name)
    except grpc.RpcError as exc:
        # TLS 핸드셰이크 실패(인증서 불일치 등)는 보통 UNAVAILABLE 로 나타난다.
        status = _GRPC_TO_HTTP.get(exc.code(), 500)
        return JsonResponse({"detail": exc.details()}, status=status)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return JsonResponse({"message": result, "elapsed_ms": elapsed_ms})
