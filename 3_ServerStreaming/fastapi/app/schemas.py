"""REST 요청/응답 스키마 (Pydantic).

gRPC 메시지를 그대로 노출하지 않고, HTTP 경계에서 쓰는 모델을 따로 둔다.
이렇게 하면 내부 proto 변경이 외부 API 계약에 곧바로 새는 것을 막을 수 있다.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    # 서버 스트리밍 RPC 의 입력은 메시지 1개다(요청 1 → 응답 여러 개).
    message: str = Field(..., min_length=1, examples=["시작"])
