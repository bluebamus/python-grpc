"""게이트웨이 뷰.

REST 엔드포인트를 노출하고 내부에서 gRPC 백엔드를 호출한다.
gRPC 상태코드를 HTTP 상태코드로 매핑한다.

엔드포인트:
- GET  /health    : 헬스 체크
- POST /echo       : Echo 비즈니스 호출
- GET  /services   : 서버 리플렉션으로 서비스 목록 조회 (이 예제의 주제)
"""

import json

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
    grpc.StatusCode.UNIMPLEMENTED: 501,
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

    try:
        result = get_client().echo(message)
    except grpc.RpcError as exc:
        status = _GRPC_TO_HTTP.get(exc.code(), 500)
        return JsonResponse({"detail": exc.details()}, status=status)

    return JsonResponse({"message": result})


@require_http_methods(["GET"])
def services(request):
    """서버 리플렉션으로 서버가 노출하는 서비스 목록을 조회한다.

    클라이언트가 .proto 를 미리 갖고 있지 않아도, 서버에 직접 물어
    어떤 서비스가 있는지 동적으로 발견할 수 있다.
    """
    try:
        names = get_client().list_services()
    except grpc.RpcError as exc:
        status = _GRPC_TO_HTTP.get(exc.code(), 500)
        return JsonResponse({"detail": exc.details()}, status=status)

    return JsonResponse({"services": names})
