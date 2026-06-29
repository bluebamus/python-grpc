"""REST 응답 스키마 (Pydantic).

gRPC 메시지를 그대로 노출하지 않고, HTTP 경계에서 쓰는 모델을 따로 둔다.
이렇게 하면 내부 proto 변경이 외부 API 계약에 곧바로 새는 것을 막을 수 있다.
"""

from pydantic import BaseModel


class GrpcHealthResponse(BaseModel):
    # 어떤 백엔드 서비스의 상태인지
    service: str
    # ServingStatus enum 이름(SERVING / NOT_SERVING / SERVICE_UNKNOWN / UNKNOWN)
    status: str
