"""게이트웨이 뷰 — threading 작업 큐 서비스.

producer(HTTP 요청)가 큐에 작업을 넣고, 데몬 consumer 스레드가 처리한다.
요청 핸들러는 작업을 큐에 넣고 즉시 task_id를 반환하므로 빠르게 응답한다.
"""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from gateway import worker


def health(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_http_methods(["POST"])
def submit_task(request):
    # 입력 파싱 + 검증
    try:
        payload_body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid JSON"}, status=400)

    payload = payload_body.get("payload")
    if not isinstance(payload, str) or not payload:
        return JsonResponse(
            {"detail": "payload는 비어있지 않은 문자열이어야 합니다."}, status=422
        )

    # producer: 큐에 작업을 넣는다. 실제 처리는 consumer 스레드가 맡는다.
    task_id = worker.submit(payload)
    return JsonResponse({"task_id": task_id, "queued": True}, status=202)


@require_http_methods(["GET"])
def get_task(request, task_id: int):
    record = worker.get_task(task_id)
    if record is None:
        return JsonResponse({"detail": "task not found"}, status=404)
    return JsonResponse(record)


@require_http_methods(["GET"])
def stats(request):
    return JsonResponse(worker.stats())
