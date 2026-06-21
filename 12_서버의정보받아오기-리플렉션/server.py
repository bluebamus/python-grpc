from concurrent import futures  # gRPC 서버가 요청을 동시에 처리할 스레드 풀(ThreadPoolExecutor)을 제공

import grpc  # gRPC 서버/채널 기능을 제공하는 핵심 라이브러리
import reflection_example_pb2  # reflection_example.proto로 생성한 메시지(EchoRequest/EchoResponse) 모듈
import reflection_example_pb2_grpc  # reflection_example.proto로 생성한 서비스 스텁/서버 등록 함수 모듈
from grpc_reflection.v1alpha import reflection  # 서버 리플렉션(클라이언트가 서버의 서비스 목록을 조회할 수 있게 함) 기능 모듈


class EchoServiceServicer(reflection_example_pb2_grpc.EchoServiceServicer):  # 생성된 EchoServiceServicer를 상속받아 실제 로직을 구현하는 클래스
    def Echo(self, request, context):  # 클라이언트가 보낸 메시지를 그대로 되돌려주는(에코) 메서드
        return reflection_example_pb2.EchoResponse(message=request.message)  # 요청의 message를 그대로 담은 응답 메시지 반환

def serve():  # 서버를 구성하고 실행하는 함수
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))  # 최대 10개 스레드로 요청을 처리하는 gRPC 서버 인스턴스 생성
    reflection_example_pb2_grpc.add_EchoServiceServicer_to_server(EchoServiceServicer(), server)  # 구현한 Echo 서비스를 서버에 등록

    SERVICE_NAMES = (  # 리플렉션으로 외부에 노출할 서비스 이름 목록
        reflection_example_pb2.DESCRIPTOR.services_by_name['EchoService'].full_name,  # EchoService의 전체 이름(reflection_example.EchoService)
        reflection.SERVICE_NAME,  # 리플렉션 서비스 자체의 이름(클라이언트가 리플렉션을 사용할 수 있도록 함께 노출)
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)  # 위 서비스 목록에 대해 서버 리플렉션 활성화

    server.add_insecure_port('[::]:50051')  # TLS 없이 모든 인터페이스(IPv6 [::])의 50051 포트에서 수신
    print("Server is running on port 50051...")  # 서버 시작 안내 메시지 출력
    server.start()  # 서버를 비동기로 시작(이 호출은 즉시 반환됨)
    server.wait_for_termination()  # 프로세스가 종료되지 않도록 서버 종료까지 대기(블로킹)


if __name__ == '__main__':
    serve()