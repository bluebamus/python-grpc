import time

import grpc
import messages_pb2
import messages_pb2_grpc


def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = messages_pb2_grpc.ChatServiceStub(channel)

        def request_generator():
            messages = ["안녕하세요!", "gRPC 양방향 스트리밍 예제입니다.", "서버와 클라이언트가 동시에 메시지를 주고받습니다."]
            for msg in messages:
                print(f"클라이언트 메시지: {msg}")
                yield messages_pb2.ChatMessage(message=msg)
                time.sleep(2)

        responses = stub.Chat(request_generator())

        for response in responses:
            print(f"수신 메시지: {response.message}")


if __name__ == '__main__':
    run()