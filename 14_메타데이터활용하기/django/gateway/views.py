"""게이트웨이 뷰.

REST 엔드포인트를 노출하고 내부에서 gRPC 백엔드를 호출한다.
이 예제의 주제는 **메타데이터**다:

- 들어온 HTTP 헤더 `Authorization`, `X-Request-Id` 를 gRPC 메타데이터로 변환·주입.
- `X-Request-Id` 가 없으면 게이트웨이가 UUID 로 생성.
- 서버가 trailing metadata 로 돌려준 값을 HTTP 응답 바디/헤더로 노출.

gRPC 상태코드는 HTTP 상태코드로 매핑한다.
"""

import json
import time
import uuid

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
        return JsonResponse(
            {"detail": "message는 비어있지 않은 문자열이어야 합니다."}, status=422
        )

    # --- HTTP 헤더 읽기 ---
    # Django 는 헤더를 request.headers 로 노출한다(대소문자 무시).
    authorization = request.headers.get("Authorization")
    # X-Request-Id 가 없으면 게이트웨이가 생성한다(분산 추적 상관키).
    request_id = request.headers.get("X-Request-Id") or f"gw-{uuid.uuid4().hex}"

    started = time.perf_counter()
    try:
        result = get_client().echo(
            message=message,
            request_id=request_id,
            authorization=authorization,
        )
    except grpc.RpcError as exc:
        status = _GRPC_TO_HTTP.get(exc.code(), 500)
        return JsonResponse({"detail": exc.details()}, status=status)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    response = JsonResponse(
        {
            "message": result.message,
            "request_id": result.request_id,
            "elapsed_ms": elapsed_ms,
        }
    )
    # 서버가 보낸 메타데이터를 HTTP 응답 헤더로도 노출한다.
    response["X-Request-Id"] = result.request_id
    response["X-Auth-Present"] = result.auth_present
    return response
