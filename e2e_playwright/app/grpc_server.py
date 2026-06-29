"""E2E 하니스용 결정론적 gRPC 서버.

- ServerStream: 요청 message 를 받아 "echo #0..#n-1" 형태로 n개 응답을 스트리밍.
- BiDi: 받은 각 메시지를 "echo: {message}" 로 즉시 되돌려준다.
실무 예제(3/5)의 동작을 결정론적으로 재현해 브라우저 검증의 기준이 된다.
"""

from concurrent import futures

import grpc

from app import proto  # noqa: F401  (sys.path 등록)
import chat_pb2
import chat_pb2_grpc


class ChatServicer(chat_pb2_grpc.ChatServiceServicer):
    def ServerStream(self, request, context):
        # 관례: message 가 "msg|n" 형태면 n개, 아니면 3개를 보낸다.
        base = request.message
        count = 3
        if "|" in base:
            base, _, n = base.partition("|")
            count = int(n) if n.isdigit() else 3
        for i in range(count):
            yield chat_pb2.ChatMessage(message=f"{base} #{i}")

    def BiDi(self, request_iterator, context):
        for msg in request_iterator:
            yield chat_pb2.ChatMessage(message=f"echo: {msg.message}")


def start_server(port: int) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(ChatServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    return server
