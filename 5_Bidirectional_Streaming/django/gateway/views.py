"""게이트웨이 뷰.

REST 엔드포인트를 노출하고 내부에서 gRPC 백엔드를 호출한다.
gRPC 상태코드를 HTTP 상태코드로 매핑한다.

이 예제는 양방향 스트리밍이지만 Django(WSGI)는 WebSocket/양방향에 부적합하므로,
`POST /chat-batch` 로 메시지 리스트를 한 번에 보내고 응답들을 모아 돌려준다.
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
}


def health(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_http_methods(["POST"])
def chat_batch(request):
    # 입력 파싱 + 검증
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid JSON"}, status=400)

    messages = payload.get("messages")
    if not isinstance(messages, list) or not all(isinstance(m, str) for m in messages):
        return JsonResponse(
            {"detail": "messages는 문자열 리스트여야 합니다."}, status=422
        )

    try:
        replies = get_client().chat_batch(messages)
    except grpc.RpcError as exc:
        status = _GRPC_TO_HTTP.get(exc.code(), 500)
        return JsonResponse({"detail": exc.details()}, status=status)

    return JsonResponse({"replies": replies})
