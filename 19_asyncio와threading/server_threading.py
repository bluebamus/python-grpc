"""threading 기반 동시성 데모.

두 개의 OS 스레드(전송/수신)가 thread-safe한 queue.Queue를 통해
메시지를 주고받는다. asyncio 버전(server_asyncio.py)과 비교하여
'멀티스레드 + 차단형 큐' 방식의 동작을 보여준다.
"""

import queue
import threading

# 스레드 간에 공유되는 thread-safe 큐.
# queue.Queue는 내부적으로 락을 사용하므로 여러 스레드가
# 동시에 put/get 해도 안전하다.
message_queue = queue.Queue()

# 수신 스레드에게 "더 이상 처리할 메시지가 없으니 종료하라"고
# 알리기 위한 고유 sentinel 객체. (일반 메시지와 절대 겹치지 않도록
# 문자열이 아닌 object() 인스턴스를 사용)
_SENTINEL = object()


def send_message():
    """사용자 입력을 받아 큐에 넣는 생산자(producer) 스레드."""
    while True:
        message = input("Enter a message to send (or 'exit' to quit): ")
        if message.lower() == 'exit':
            # 종료 전에 sentinel을 넣어 수신 스레드도 함께 멈추게 한다.
            # 이 신호가 없으면 receive_message가 영원히 대기하여
            # receive_thread.join()이 끝나지 않고 프로그램이 멈춘다.
            message_queue.put(_SENTINEL)
            break
        message_queue.put(message)
        print(f"Message sent: {message}")


def receive_message():
    """큐에서 메시지를 꺼내 출력하는 소비자(consumer) 스레드."""
    while True:
        # 차단형(blocking) get(): 큐가 비어 있으면 항목이 들어올 때까지
        # 대기한다. empty()를 폴링하는 방식과 달리 CPU를 낭비하는
        # busy-wait가 발생하지 않는다.
        message = message_queue.get()
        if message is _SENTINEL:
            # 종료 신호를 받으면 루프를 빠져나가 스레드를 끝낸다.
            break
        print(f"Message received: {message}")


def main():
    # 전송/수신을 각각 별도의 스레드에서 실행한다.
    send_thread = threading.Thread(target=send_message)
    receive_thread = threading.Thread(target=receive_message)

    send_thread.start()
    receive_thread.start()

    # 두 스레드가 모두 끝날 때까지 메인 스레드가 대기한다.
    send_thread.join()
    receive_thread.join()


if __name__ == "__main__":
    main()
