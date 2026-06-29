"""게이트웨이 뷰.

REST 엔드포인트를 노출하고 내부에서 gRPC 표준 헬스체크(Check)를 호출한다.
ServingStatus 와 gRPC 상태코드를 HTTP 상태코드로 매핑한다.
"""

import grpc
from django.conf import settings  # noqa: F401  (settings 로드 보장)
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from gateway import proto  # noqa: F401  (proto sys.path 등록)
import health_check_pb2
from gateway.grpc_client import get_client

# ServingStatus(int) -> (이름, HTTP status). SERVING 만 200, 나머지는 503.
_Status = health_check_pb2.HealthCheckResponse
_STATUS_TO_HTTP: dict[int, tuple[str, int]] = {
    _Status.SERVING: ("SERVING", 200),
    _Status.NOT_SERVING: ("NOT_SERVING", 503),
    _Status.SERVICE_UNKNOWN: ("SERVICE_UNKNOWN", 503),
    _Status.UNKNOWN: ("UNKNOWN", 503),
}

# gRPC StatusCode -> HTTP status (Check 자체가 에러로 끝난 경우).
_GRPC_TO_HTTP = {
    grpc.StatusCode.UNAVAILABLE: 503,
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.PERMISSION_DENIED: 403,
    grpc.StatusCode.UNAUTHENTICATED: 401,
}


@require_http_methods(["GET"])
def health(request):
    """게이트웨이 자체 헬스. 백엔드와 무관하게 항상 200."""
    return JsonResponse({"status": "ok"})


@require_http_methods(["GET"])
def health_grpc(request):
    """백엔드 gRPC 서비스의 헬스 상태를 Check 로 조회해 HTTP 로 노출한다."""
    service = request.GET.get("service", "")
    try:
        status_value = get_client().check(service)
    except grpc.RpcError as exc:
        status = _GRPC_TO_HTTP.get(exc.code(), 500)
        return JsonResponse(
            {"service": service, "status": "SERVICE_UNKNOWN"}, status=status
        )

    name, http_status = _STATUS_TO_HTTP.get(status_value, ("UNKNOWN", 503))
    return JsonResponse({"service": service, "status": name}, status=http_status)
