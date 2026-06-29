"""게이트웨이 뷰 — protobuf 직렬화 데모 (Django).

이 예제(1_bookstore)에는 gRPC 서비스가 없으므로 외부 호출이 없다. REST 로
JSON 을 받아 protobuf 메시지로 변환해 직렬화하고, 그 바이너리를 다시
역직렬화한다. Pydantic 이 없으므로 필수 필드 검증을 직접 수행하고, 누락 시
422 를 반환한다.
"""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from gateway import serializer


def _parse_json(request):
    """요청 본문을 JSON 으로 파싱한다. 실패 시 (None, 에러응답) 을 반환."""
    try:
        return json.loads(request.body or b"{}"), None
    except json.JSONDecodeError:
        return None, JsonResponse({"detail": "invalid JSON"}, status=400)


def _require(payload: dict, fields: list[str]):
    """필수 필드가 비어있지 않은 문자열인지 검증한다. 누락 시 422 응답을 반환."""
    for field in fields:
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            return JsonResponse(
                {"detail": f"'{field}'는 비어있지 않은 문자열이어야 합니다."},
                status=422,
            )
    return None


def health(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_http_methods(["POST"])
def serialize_book(request):
    """JSON Book -> protobuf 직렬화. 크기/base64 와 왕복 일치 여부를 반환한다."""
    payload, err = _parse_json(request)
    if err:
        return err
    err = _require(payload, ["isbn", "title"])
    if err:
        return err

    book = serializer.build_book(payload)
    data = serializer.serialize(book)
    return JsonResponse(
        {
            "book": serializer.book_to_dict(serializer.parse_book(data)),
            "serialized_size": len(data),
            "serialized_base64": serializer.to_base64(data),
            "roundtrip_ok": serializer.roundtrip_book(book),
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def serialize_order(request):
    """JSON Order -> protobuf 직렬화 (중첩 customer + repeated items)."""
    payload, err = _parse_json(request)
    if err:
        return err
    err = _require(payload, ["order_number"])
    if err:
        return err
    customer = payload.get("customer")
    if not isinstance(customer, dict) or not customer.get("id") or not customer.get("name"):
        return JsonResponse(
            {"detail": "customer.id 와 customer.name 은 필수입니다."}, status=422
        )
    items = payload.get("items")
    if not isinstance(items, list) or len(items) == 0:
        return JsonResponse({"detail": "items 는 1개 이상이어야 합니다."}, status=422)

    order = serializer.build_order(payload)
    data = serializer.serialize(order)
    return JsonResponse(
        {
            "order_number": order.order_number,
            "item_count": len(order.items),
            "serialized_size": len(data),
            "serialized_base64": serializer.to_base64(data),
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def decode_book(request):
    """base64(직렬화된 Book bytes) -> 역직렬화 -> JSON."""
    payload, err = _parse_json(request)
    if err:
        return err
    err = _require(payload, ["data_base64"])
    if err:
        return err

    data = serializer.from_base64(payload["data_base64"])
    book = serializer.parse_book(data)
    return JsonResponse({"book": serializer.book_to_dict(book)})
