"""threading 기반 인메모리 작업 큐 (producer/consumer).

server_threading.py 데모를 웹 서비스로 실무화한 것이다. 데모에서는
input()으로 받은 메시지를 queue.Queue로 넘겼다면, 여기서는 HTTP
요청(producer)이 작업을 큐에 넣고, 앱 로드 시 1회 기동된 데몬
consumer 스레드가 큐를 비우며 처리한다.

asyncio 샘플과의 대비:
- asyncio: 단일 스레드 + 이벤트 루프 + await(협력적). 락 불필요.
- threading: 여러 OS 스레드 + 차단형 queue.Queue.get(). 공유 상태(작업
  저장소/카운터)는 GIL이 있어도 복합 연산의 원자성을 위해 락으로 보호한다.

WSGI(동기) 서버에서 요청 핸들러는 블로킹이 자연스럽다. 무거운 작업을
요청 안에서 직접 하면 워커가 묶이므로, 별도 스레드(여기서는 consumer)에
위임해 요청은 즉시 task_id만 돌려준다.
"""

import itertools
import queue
import threading
import time

from django.conf import settings

# --- 스레드 간 공유 상태 ---
# queue.Queue는 내부적으로 락을 사용하므로 여러 스레드가 동시에 put/get 해도 안전하다.
_queue: "queue.Queue[int]" = queue.Queue()

# 작업 저장소/카운터는 일반 dict/int 이므로, 복합 연산(읽고-쓰기)을
# 보호하기 위해 명시적 락을 둔다.
_tasks: dict[int, dict] = {}
_lock = threading.Lock()
_ids = itertools.count(1)
_processed = 0

# consumer 스레드 기동을 1회로 제한하기 위한 가드.
_started = False
_start_lock = threading.Lock()
_thread: threading.Thread | None = None


def _process_delay() -> float:
    return getattr(settings, "WORKER_PROCESS_DELAY", 0.01)


def _process(payload: str) -> str:
    """동기/차단형 작업을 흉내내는 함수.

    time.sleep으로 스레드를 멈춘다(외부 API/이미지 변환/DB 작업 등 모사).
    threading 모델에서는 이런 블로킹이 consumer 스레드만 멈출 뿐,
    요청 스레드/다른 스레드는 OS 스케줄러가 계속 돌린다.
    """
    time.sleep(_process_delay())
    return payload.upper()


def submit(payload: str) -> int:
    """producer: 작업을 만들어 큐에 넣고 task_id를 돌려준다."""
    with _lock:
        task_id = next(_ids)
        _tasks[task_id] = {
            "task_id": task_id,
            "payload": payload,
            "status": "queued",
            "result": None,
        }
    _queue.put(task_id)
    return task_id


def get_task(task_id: int) -> dict | None:
    with _lock:
        record = _tasks.get(task_id)
        # 호출자가 내부 상태를 직접 건드리지 못하도록 복사본을 돌려준다.
        return dict(record) if record is not None else None


def stats() -> dict:
    with _lock:
        return {
            "processed": _processed,
            "pending": _queue.qsize(),
            "total": len(_tasks),
        }


def _consume() -> None:
    """consumer: 큐에서 작업을 꺼내 처리하는 데몬 스레드 루프.

    차단형 get(): 큐가 비면 항목이 들어올 때까지 대기한다. empty()를
    폴링하는 방식과 달리 CPU를 낭비하는 busy-wait가 없다.
    """
    global _processed
    while True:
        task_id = _queue.get()
        try:
            with _lock:
                _tasks[task_id]["status"] = "processing"
                payload = _tasks[task_id]["payload"]
            result = _process(payload)  # 락 밖에서 처리(다른 스레드를 막지 않음)
            with _lock:
                _tasks[task_id]["result"] = result
                _tasks[task_id]["status"] = "done"
                _processed += 1
        finally:
            _queue.task_done()


def start_worker() -> None:
    """consumer 데몬 스레드를 1회만 기동한다(중복 기동 방지 가드).

    데몬 스레드라 메인 프로세스 종료 시 함께 정리된다. 별도의 그레이스풀
    셧다운 훅이 필요하면 sentinel을 큐에 넣어 루프를 빠져나오게 한다(데모 참고).
    """
    global _started, _thread
    with _start_lock:
        if _started:
            return
        _thread = threading.Thread(target=_consume, name="task-consumer", daemon=True)
        _thread.start()
        _started = True
