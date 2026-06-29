"""asyncio 기반 동시성 데모.

단일 스레드의 이벤트 루프 위에서 두 개의 코루틴(전송/수신)이
asyncio.Queue를 통해 메시지를 주고받는다. threading 버전
(server_threading.py)과 비교하여 '단일 스레드 + 협력적 동시성'
방식의 동작을 보여준다.

핵심 포인트: input()처럼 동기적으로 블로킹되는 호출은
asyncio.to_thread()로 감싸 별도 스레드에서 실행해야 이벤트 루프가
멈추지 않는다.
"""

import asyncio

# asyncio 환경에서는 코루틴 간 통신에 asyncio.Queue가 관용적이다.
# put/get이 코루틴(await 대상)이라 이벤트 루프와 자연스럽게 협력한다.
message_queue: asyncio.Queue = asyncio.Queue()

# 수신 코루틴에게 종료를 알리는 고유 sentinel 객체.
# (일반 메시지와 겹치지 않도록 object() 인스턴스 사용)
_SENTINEL = object()


async def send_message():
    """사용자 입력을 받아 큐에 넣는 생산자(producer) 코루틴."""
    while True:
        # input()은 동기 차단 호출이다. 그냥 호출하면 입력을 기다리는
        # 동안 이벤트 루프 전체가 멈춰 receive_message가 실행되지
        # 못한다. to_thread로 별도 스레드에서 돌려 루프를 살려 둔다.
        message = await asyncio.to_thread(input, "Enter a message (or 'exit' to quit): ")
        if message.lower() == 'exit':
            # 수신 코루틴도 함께 멈추도록 종료 신호를 큐에 넣는다.
            await message_queue.put(_SENTINEL)
            break
        await message_queue.put(message)


async def receive_message():
    """큐에서 메시지를 꺼내 출력하는 소비자(consumer) 코루틴."""
    while True:
        # 항목이 들어올 때까지 비동기로 대기한다. 대기 중에는 제어권을
        # 이벤트 루프에 넘기므로 busy-wait가 없고 다른 코루틴이 실행된다.
        message = await message_queue.get()
        if message is _SENTINEL:
            break
        print(f"Received: {message}")


async def main():
    # 두 코루틴을 동시에 실행하고 모두 끝날 때까지 기다린다.
    await asyncio.gather(
        send_message(),
        receive_message()
    )


if __name__ == '__main__':
    # 이벤트 루프를 생성하고 main() 코루틴을 실행한다.
    asyncio.run(main())
