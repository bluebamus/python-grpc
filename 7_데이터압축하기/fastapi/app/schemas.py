"""REST 응답 스키마 (Pydantic).

gRPC 메시지를 그대로 노출하지 않고, HTTP 경계에서 쓰는 모델을 따로 둔다.
gRPC 의 bytes 는 JSON 으로 그대로 실을 수 없으므로 base64 문자열로 인코딩해
전달한다.
"""

from pydantic import BaseModel


class DataResponse(BaseModel):
    data_id: str
    # 원본 bytes 를 base64 로 인코딩한 문자열
    data_base64: str
    # 디코딩된 원본 바이트 길이
    size: int
    # 관측용: 게이트웨이가 응답을 받기까지 걸린 시간(ms)
    elapsed_ms: float
