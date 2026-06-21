import grpc  # gRPC 클라이언트/채널 기능을 제공하는 핵심 라이브러리
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc  # 서버 리플렉션 프로토콜의 메시지(reflection_pb2)와 스텁(reflection_pb2_grpc)


def run():  # 서버에 리플렉션 요청을 보내 서비스 목록을 조회/출력하는 함수
    with grpc.insecure_channel('localhost:50051') as channel:  # TLS 없이 localhost:50051 서버에 연결되는 채널 생성(with 종료 시 자동 닫힘)
        stub = reflection_pb2_grpc.ServerReflectionStub(channel)  # 채널을 이용해 리플렉션 서비스의 원격 메서드를 호출할 스텁 생성

        request = reflection_pb2.ServerReflectionRequest(  # 리플렉션 요청 메시지 생성
            list_services="*"  # 서버가 노출하는 모든 서비스 목록을 요청('*'가 표준 관례)
        )

        response = stub.ServerReflectionInfo(iter([request]))  # 요청을 스트림(이터레이터)으로 보내고 응답 스트림을 받음(양방향 스트리밍 RPC)
        for service in response:  # 서버가 보낸 응답(ServerReflectionResponse)을 하나씩 반복 수신
            for service_response in service.list_services_response.service:  # 응답 안의 서비스 목록을 하나씩 순회
                print(f"Service: {service_response.name}")  # 각 서비스의 전체 이름을 출력

if __name__ == '__main__':
    print("Running reflection client...")
    run()