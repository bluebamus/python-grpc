"""REST/WebSocket 경계의 메시지 모델 (Pydantic).

이 예제의 본 채널은 WebSocket(`/ws/chat`)이며, 클라이언트와 게이트웨이는
평문 텍스트 프레임을 주고받는다. gRPC `ChatMessage` 를 그대로 노출하지 않고,
HTTP/WebSocket 경계에서 쓰는 모델을 따로 둠으로써 내부 proto 변경이 외부
계약으로 곧바로 새는 것을 막는다.

WebSocket 은 자유 텍스트라 강제 스키마가 필수는 아니지만, health 응답처럼
구조화가 필요한 곳과 향후 확장을 위해 모델을 정의해 둔다.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
