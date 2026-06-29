"""FastAPI 앱 — asyncio 동시성 모델 기반 작업 큐 서비스.

producer(HTTP 요청)가 asyncio.Queue에 작업을 넣고, lifespan에서 기동된
백그라운드 consumer 코루틴이 큐를 비우며 처리한다. 같은 이벤트 루프
위에서 요청 처리와 작업 소비가 협력적으로 동시에 진행된다.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.config import settings
from app.schemas import Stats, SubmitRequest, SubmitResponse, TaskStatus
from app.worker import AsyncTaskQueue


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 기동 시 큐를 만들고 consumer 코루틴을 띄운다.
    # 큐는 반드시 실행 중인 이벤트 루프 안에서 생성한다.
    queue = AsyncTaskQueue(
        process_delay=settings.process_delay,
        maxsize=settings.queue_maxsize,
    )
    queue.start()
    app.state.queue = queue
    try:
        yield
    finally:
        # 그레이스풀 셧다운: 남은 작업을 처리한 뒤 consumer를 정리한다.
        await queue.stop()


app = FastAPI(title="asyncio 작업 큐 서비스", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tasks", response_model=SubmitResponse, status_code=202)
async def submit_task(req: SubmitRequest) -> SubmitResponse:
    # producer: 큐에 작업을 넣는다. await put은 즉시 반환(무제한 큐)하므로
    # 응답이 빠르고, 실제 처리는 백그라운드 consumer가 맡는다.
    queue: AsyncTaskQueue = app.state.queue
    task_id = await queue.submit(req.payload)
    return SubmitResponse(task_id=task_id, queued=True)


@app.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: int) -> TaskStatus:
    queue: AsyncTaskQueue = app.state.queue
    record = queue.get(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskStatus(**record)


@app.get("/stats", response_model=Stats)
def stats() -> Stats:
    queue: AsyncTaskQueue = app.state.queue
    return Stats(**queue.stats())
