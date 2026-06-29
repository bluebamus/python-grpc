"""REST 요청/응답 스키마 (Pydantic).

gRPC 메시지를 그대로 노출하지 않고, HTTP 경계에서 쓰는 모델을 따로 둔다.
이렇게 하면 내부 proto 변경이 외부 API 계약에 곧바로 새는 것을 막을 수 있다.
"""

from pydantic import BaseModel, Field


class StreamDataRequest(BaseModel):
    # 클라이언트 스트리밍의 입력: 게이트웨이가 이 리스트의 각 원소를
    # RequestMessage 로 변환해 gRPC 요청 스트림으로 흘려보낸다.
    # min_length=1 로 빈 리스트를 막아 검증 실패(422)를 유도한다.
    items: list[str] = Field(..., min_length=1, examples=[["a", "b", "c"]])


class StreamDataResponse(BaseModel):
    # 서버가 요청 스트림을 모두 받은 뒤 집계해 돌려준 단일 결과 문자열
    result: str
    # 게이트웨이가 보낸 요청(아이템) 개수
    count: int
    # 디버깅/관측용: 게이트웨이가 응답을 받기까지 걸린 시간(ms)
    elapsed_ms: float
