"""REST 요청/응답 스키마 (Pydantic).

gRPC 메시지를 그대로 노출하지 않고, HTTP 경계에서 쓰는 모델을 따로 둔다.
이렇게 하면 내부 proto 변경이 외부 API 계약에 곧바로 새는 것을 막을 수 있다.
"""

from pydantic import BaseModel, Field


class HelloRequest(BaseModel):
    name: str = Field(..., min_length=1, examples=["World"])


class HelloResponse(BaseModel):
    message: str
    # 디버깅/관측용: 게이트웨이가 응답을 받기까지 걸린 시간(ms)
    elapsed_ms: float
