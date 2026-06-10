import grpc  # gRPC 핵심 라이브러리 (채널 생성 등)
import message_pb2  # protoc로 생성된 메시지 클래스 모듈 (ChatMessage)
import message_pb2_grpc  # protoc로 생성된 서비스 stub 모듈


def run():
    with grpc.insecure_channel('localhost:50051') as channel:  # 서버에 암호화 없는 채널 연결, with 종료 시 자동 close
        stub = message_pb2_grpc.ChatServiceStub(channel)       # ChatService 호출용 stub(클라이언트) 생성
        print("서버로부터 메시지를 받는 중...")
        for message in stub.ChatStream(message_pb2.ChatMessage(message="시작")):  # 요청 1개 전송 → 응답 stream을 반복 수신
            print(f"수신 메시지: {message.message}")           # 서버가 스트리밍으로 보낸 각 메시지를 출력


if __name__ == '__main__':                                # 스크립트가 직접 실행될 때만
    run()                                                 # 클라이언트 실행
