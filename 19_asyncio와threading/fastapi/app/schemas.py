"""REST 요청/응답 스키마 (Pydantic).

HTTP 경계에서 쓰는 모델을 따로 둔다. 내부 작업 레코드(dict) 구조가
외부 API 계약으로 곧바로 새는 것을 막는다.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SubmitRequest(BaseModel):
    payload: str = Field(..., min_length=1, examples=["hello world"])


class SubmitResponse(BaseModel):
    task_id: int
    queued: bool


class TaskStatus(BaseModel):
    task_id: int
    # queued -> processing -> done 으로 진행한다.
    status: Literal["queued", "processing", "done"]
    payload: str
    result: Optional[str] = None


class Stats(BaseModel):
    processed: int  # consumer가 완료한 누적 작업 수
    pending: int    # 아직 큐에 남아 처리 대기 중인 작업 수
    total: int      # 지금까지 제출된 전체 작업 수
