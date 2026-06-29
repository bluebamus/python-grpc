"""게이트웨이 뷰 (서버 스트리밍 → HTTP 스트리밍).

REST 엔드포인트를 노출하고 내부에서 gRPC 서버 스트리밍 RPC(ChatStream)를
호출한다. 요청 1개에 대한 응답 stream 을 모아서 주지 않고, StreamingHttpResponse
로 도착하는 대로 SSE(text/event-stream) 청크로 흘려보낸다.
"""

import json

import grpc
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from gateway.grpc_client import get_client

# gRPC StatusCode -> HTTP status 매핑.
# 스트림이 시작되기 전에 발생한 오류만 일반 HTTP 에러로 응답할 수 있다.
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


def _sse(data: dict) -> str:
    """dict 를 SSE 한 이벤트(`data: {json}\\n\\n`)로 직렬화한다."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@csrf_exempt
@require_http_methods(["POST"])
def chat_stream(request):
    # 입력 파싱 + 검증
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid JSON"}, status=400)
    message = payload.get("message")
    if not isinstance(message, str) or not message:
        return JsonResponse({"detail": "message는 비어있지 않은 문자열이어야 합니다."}, status=422)

    # 첫 메시지를 미리 한 번 당겨본다(peek). 스트림이 시작되기 전(=헤더가 나가기
    # 전)에 발생하는 오류는 여기서 HTTP 상태코드로 매핑할 수 있다.
    stream = get_client().chat_stream(message)
    try:
        first = next(stream)
        has_first = True
    except StopIteration:
        first = None
        has_first = False  # 메시지가 0개인 정상 스트림
    except grpc.RpcError as exc:
        status = _GRPC_TO_HTTP.get(exc.code(), 500)
        return JsonResponse({"detail": exc.details()}, status=status)

    def event_generator():
        index = 0
        if has_first:
            yield _sse({"index": index, "message": first})
            index += 1
        try:
            for msg in stream:
                yield _sse({"index": index, "message": msg})
                index += 1
        except grpc.RpcError as exc:
            # 스트림 도중 실패: 상태코드는 못 바꾸므로 error 이벤트로 알린다.
            yield (
                "event: error\n"
                f"data: {json.dumps({'code': exc.code().name, 'detail': exc.details()}, ensure_ascii=False)}\n\n"
            )
            return
        # 정상 종료를 알리는 done 이벤트 (총 개수 포함)
        yield f"event: done\ndata: {json.dumps({'count': index}, ensure_ascii=False)}\n\n"

    response = StreamingHttpResponse(
        event_generator(), content_type="text/event-stream"
    )
    # 프록시/서버 버퍼링을 끄도록 힌트를 준다(스트리밍 효과 보존).
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
