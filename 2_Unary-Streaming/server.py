from concurrent import \
    futures  # ThreadPoolExecutor 제공: gRPC 서버가 여러 요청을 스레드 풀로 동시 처리하기 위해 import

import grpc
import helloworld_pb2
import helloworld_pb2_grpc


class Greeter(helloworld_pb2_grpc.GreeterServicer):  # Greeter 서비스 구현을 위한 클래스 정의
    def SayHello(self, request, context):              # SayHello 메서드 구현, 클라이언트 요청과 gRPC 컨텍스트 인자 받음
        return helloworld_pb2.HelloReply(message='Hello, %s!' % request.name)  # 요청에서 name 추출하여 응답 메시지 생성    

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))  # gRPC 서버 생성, 최대 10개의 스레드로 요청 처리
    helloworld_pb2_grpc.add_GreeterServicer_to_server(Greeter(), server)  # Greeter 서비스 구현체를 서버에 등록
    server.add_insecure_port('[::]:50051')  # 서버가 모든 인터페이스에서 포트 50051로 수신하도록 설정
    server.start()  # 서버 시작
    print("Server started on port 50051.")
    server.wait_for_termination()  # 서버가 종료될 때까지 대기

if __name__ == '__main__':  # 스크립트가 직접 실행될 때만
    serve()  # serve() 호출하여 서버 실행