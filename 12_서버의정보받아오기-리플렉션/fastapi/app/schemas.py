"""REST 요청/응답 스키마 (Pydantic).

gRPC 메시지를 그대로 노출하지 않고, HTTP 경계에서 쓰는 모델을 따로 둔다.
이렇게 하면 내부 proto 변경이 외부 API 계약에 곧바로 새는 것을 막을 수 있다.
"""

from pydantic import BaseModel, Field


class EchoRequest(BaseModel):
    message: str = Field(..., min_length=1, examples=["Hello"])


class EchoResponse(BaseModel):
    message: str


class ServicesResponse(BaseModel):
    # 서버 리플렉션으로 발견한 서비스 전체 이름 목록
    services: list[str]
