"""게이트웨이 뷰.

REST 엔드포인트를 노출하고 내부에서 gRPC 백엔드를 호출한다.
이 예제의 주제는 **에러 핸들링**이다: gRPC StatusCode 를 의미가 맞는 HTTP
상태코드로 충실히 매핑하고, 서버가 내려준 에러 상세(details)도 응답에 담는다.
"""

import json
import time

import grpc
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from gateway.grpc_client import get_client

# gRPC StatusCode -> HTTP status 매핑 표 (16종 전체).
_GRPC_TO_HTTP: dict[grpc.StatusCode, int] = {
    grpc.StatusCode.OK: 200,
    grpc.StatusCode.CANCELLED: 499,
    grpc.StatusCode.UNKNOWN: 500,
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.ALREADY_EXISTS: 409,
    grpc.StatusCode.PERMISSION_DENIED: 403,
    grpc.StatusCode.UNAUTHENTICATED: 401,
    grpc.StatusCode.RESOURCE_EXHAUSTED: 429,
    grpc.StatusCode.FAILED_PRECONDITION: 400,
    grpc.StatusCode.ABORTED: 409,
    grpc.StatusCode.OUT_OF_RANGE: 400,
    grpc.StatusCode.UNIMPLEMENTED: 501,
    grpc.StatusCode.INTERNAL: 500,
    grpc.StatusCode.UNAVAILABLE: 503,
    grpc.StatusCode.DATA_LOSS: 500,
}


def health(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_http_methods(["POST"])
def divide(request):
    # 입력 파싱 + 검증
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid JSON"}, status=400)

    dividend = payload.get("dividend")
    divisor = payload.get("divisor")
    # 숫자(bool 제외)인지 검증한다. divisor 의 0 여부는 서버가 판정한다.
    if not _is_number(dividend) or not _is_number(divisor):
        return JsonResponse(
            {"detail": "dividend, divisor 는 숫자여야 합니다."}, status=422
        )

    started = time.perf_counter()
    try:
        quotient = get_client().divide(float(dividend), float(divisor))
    except grpc.RpcError as exc:
        # 핵심: gRPC 에러를 HTTP 로 변환한다.
        # 서버는 divisor=0 일 때 INVALID_ARGUMENT 로 abort -> HTTP 400.
        code = exc.code()
        http_status = _GRPC_TO_HTTP.get(code, 500)
        return JsonResponse(
            {
                "error": {
                    "grpc_status": code.name,
                    "http_status": http_status,
                    "detail": exc.details(),
                }
            },
            status=http_status,
        )

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return JsonResponse({"quotient": quotient, "elapsed_ms": elapsed_ms})


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
