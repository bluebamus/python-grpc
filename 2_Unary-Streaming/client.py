import grpc                                          # gRPC 핵심 라이브러리 (채널 생성 등)
import helloworld_pb2                                 # protoc로 생성된 메시지 클래스 모듈
import helloworld_pb2_grpc                            # protoc로 생성된 서비스 stub 모듈


def run():
    with grpc.insecure_channel('localhost:50051') as channel:  # 서버(localhost:50051)에 암호화 없는 채널 연결, with 블록 종료 시 자동 close
        stub = helloworld_pb2_grpc.GreeterStub(channel)        # 채널을 이용해 Greeter 서비스 호출용 stub(클라이언트) 생성
        response = stub.SayHello(helloworld_pb2.HelloRequest(name='Alice'))  # name='Alice' 요청 전송 후 응답(HelloReply) 수신
    print("Greeter client received: " + response.message)      # 서버가 보낸 응답 메시지 출력


if __name__ == '__main__':                            # 스크립트가 직접 실행될 때만
    run()                                             # run() 호출
