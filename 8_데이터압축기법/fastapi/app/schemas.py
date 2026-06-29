"""REST 요청/응답 스키마 (Pydantic).

gRPC 메시지를 그대로 노출하지 않고, HTTP 경계에서 쓰는 모델을 따로 둔다.
proto 의 `bytes data` 는 JSON 으로 그대로 실을 수 없으므로 base64 로 인코딩해
문자열 필드(`data_base64`)로 노출한다.
"""

from pydantic import BaseModel


class DataResponse(BaseModel):
    data_id: str
    # proto 의 bytes 페이로드를 base64 문자열로 인코딩한 값
    data_base64: str
    # 복원된 원본 바이트 크기(압축 알고리즘과 무관하게 동일해야 한다)
    size: int
    # 이 호출에 실제로 적용된 압축 알고리즘 (none / deflate / gzip)
    compression: str
    # 관측용: 게이트웨이가 응답을 받기까지 걸린 시간(ms)
    elapsed_ms: float
