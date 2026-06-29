"""asyncio 기반 인메모리 작업 큐 (producer/consumer).

server_asyncio.py 데모를 웹 서비스로 실무화한 것이다. 데모에서는
input()으로 메시지를 받아 asyncio.Queue로 넘겼다면, 여기서는 HTTP
요청(producer)이 작업을 큐에 넣고, lifespan에서 기동된 백그라운드
consumer 코루틴이 큐를 비우며 처리한다.

핵심 교훈(데모 주석 그대로): input()/time.sleep 같은 동기 차단 호출을
코루틴에서 그냥 부르면 이벤트 루프 전체가 멈춘다. 반드시
asyncio.to_thread()로 감싸 별도 스레드에서 돌려야 루프가 살아 있어
다른 요청과 consumer가 계속 실행된다.
"""

import asyncio
import itertools
import time
from typing import Optional


def _blocking_process(payload: str, delay: float) -> str:
    """동기/차단형 작업을 흉내내는 함수.

    time.sleep은 CPU를 양보하지 않고 호출 스레드를 그대로 멈춘다. 이런
    함수를 consumer 코루틴에서 직접 await 없이 호출하면 이벤트 루프가
    멈춘다. 그래서 호출부에서 asyncio.to_thread로 감싸 별도 스레드에서
    실행한다. (실무라면 여기서 외부 API 호출/이미지 변환/DB 작업 등을 한다)
    """
    time.sleep(delay)
    return payload.upper()


class AsyncTaskQueue:
    """asyncio.Queue 기반 작업 큐 + 인메모리 작업 저장소.

    단일 이벤트 루프 위에서 동작하므로 작업 레코드(dict) 접근에 락이
    필요 없다(협력적 동시성: await 지점에서만 제어가 넘어간다). 이는
    멀티스레드(threading 샘플)가 queue.Queue/락을 써야 하는 것과 대비된다.
    """

    def __init__(self, process_delay: float = 0.01, maxsize: int = 0) -> None:
        self._process_delay = process_delay
        # asyncio.Queue는 코루틴 친화적이다. put/get이 await 대상이라
        # 이벤트 루프와 자연스럽게 협력한다. maxsize>0이면 백프레셔가 걸린다.
        self._queue: asyncio.Queue[int] = asyncio.Queue(maxsize=maxsize)
        self._tasks: dict[int, dict] = {}
        self._ids = itertools.count(1)
        self._processed = 0
        self._consumer: Optional[asyncio.Task] = None

    async def submit(self, payload: str) -> int:
        """producer: 작업을 만들어 큐에 넣고 task_id를 돌려준다.

        await queue.put은 큐가 가득 찼을 때만(maxsize>0) 대기한다. 그
        외에는 즉시 반환하므로 요청 핸들러를 오래 붙잡지 않는다.
        """
        task_id = next(self._ids)
        self._tasks[task_id] = {
            "task_id": task_id,
            "payload": payload,
            "status": "queued",
            "result": None,
        }
        await self._queue.put(task_id)
        return task_id

    def get(self, task_id: int) -> Optional[dict]:
        return self._tasks.get(task_id)

    def stats(self) -> dict:
        return {
            "processed": self._processed,
            "pending": self._queue.qsize(),
            "total": len(self._tasks),
        }

    def start(self) -> None:
        """백그라운드 consumer 코루틴을 기동한다(lifespan 시작 시 1회)."""
        if self._consumer is None or self._consumer.done():
            self._consumer = asyncio.create_task(self._consume())

    async def stop(self) -> None:
        """그레이스풀 셧다운: 큐에 남은 작업을 모두 처리한 뒤 종료한다.

        queue.join()은 put된 항목 수만큼 task_done()이 호출될 때까지
        기다린다. 이렇게 하면 종료 중 유실되는 작업이 없다. 처리를 끝낸
        뒤 consumer 코루틴을 취소한다.
        """
        if self._consumer is None:
            return
        await self._queue.join()
        self._consumer.cancel()
        try:
            await self._consumer
        except asyncio.CancelledError:
            pass
        self._consumer = None

    async def _consume(self) -> None:
        """consumer: 큐에서 작업을 꺼내 처리하는 백그라운드 코루틴.

        await queue.get()은 항목이 들어올 때까지 비동기로 대기하며,
        대기 중에는 제어를 이벤트 루프에 넘긴다(busy-wait 없음). 이 덕에
        consumer가 대기하는 동안에도 다른 HTTP 요청이 처리된다.
        """
        while True:
            task_id = await self._queue.get()
            try:
                record = self._tasks[task_id]
                record["status"] = "processing"
                # 블로킹 함수는 to_thread로 감싸 이벤트 루프를 보호한다.
                result = await asyncio.to_thread(
                    _blocking_process, record["payload"], self._process_delay
                )
                record["result"] = result
                record["status"] = "done"
                self._processed += 1
            finally:
                # join()이 끝나려면 get한 항목마다 task_done이 필요하다.
                self._queue.task_done()
