import time  # 메시지 사이 지연(sleep)을 주기 위해 import
from concurrent import futures  # ThreadPoolExecutor 제공: 여러 요청을 스레드 풀로 동시 처리

import grpc  # gRPC 핵심 라이브러리 (서버 생성 등)
import message_pb2  # protoc로 생성된 메시지 클래스 모듈 (ChatMessage)
import message_pb2_grpc  # protoc로 생성된 서비스 servicer/stub 모듈


class ChatService(message_pb2_grpc.ChatServiceServicer):  # ChatService 서비스 구현 클래스
    def ChatStream(self, request, context):               # proto의 RPC 이름과 동일해야 함. Server Streaming이므로 request는 단일 객체
        messages = [                                      # 클라이언트에게 순차적으로 보낼 메시지 목록
            "안녕하세요!",
            "gRPC 서버 스트리밍 예제입니다.",
            "여러 메시지를 순차적으로 보내 드립니다."
        ]
        for message in messages:                          # 목록을 하나씩 순회하며
            yield message_pb2.ChatMessage(message=message)  # yield로 응답을 스트리밍 (return 아님 → 여러 번 전송)
            time.sleep(1)                                 # 메시지 간에 1초 대기 (스트리밍 효과 확인용)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))    # gRPC 서버 생성, 최대 10개 스레드로 처리
    message_pb2_grpc.add_ChatServiceServicer_to_server(ChatService(), server)  # 구현체를 서버에 등록
    server.add_insecure_port('[::]:50051')                # 모든 인터페이스에서 포트 50051 수신 (암호화 없음)
    server.start()                                        # 서버 시작 (논블로킹)
    print("Server started on port 50051.")
    server.wait_for_termination()                         # 서버가 종료될 때까지 대기


if __name__ == '__main__':                                # 스크립트가 직접 실행될 때만
    serve()                                               # 서버 실행
