import grpc  # gRPC 클라이언트/채널 기능을 제공하는 핵심 라이브러리
import health_check_pb2  # health_check.proto로 생성한 메시지(HealthCheckRequest/Response) 모듈
import health_check_pb2_grpc  # health_check.proto로 생성한 서비스 스텁 모듈


def run_check():  # 서버 상태를 1회성(unary)으로 조회하는 함수 정의
    with grpc.insecure_channel('localhost:50051') as channel:  # TLS 없이 localhost:50051 서버에 연결되는 채널 생성(with 블록 종료 시 자동 닫힘)
        stub = health_check_pb2_grpc.healthStub(channel)  # 채널을 이용해 health 서비스의 원격 메서드를 호출할 수 있는 스텁 생성
        request = health_check_pb2.HealthCheckRequest(service='my_service')  # 'my_service' 서비스의 상태를 묻는 요청 메시지 생성
        response = stub.Check(request)  # 서버의 Check 메서드를 호출하여 현재 상태를 1회 응답으로 받음
        print(f"Health check status for 'my_service': {response.status}")  # 응답으로 받은 상태값(status) 출력

def run_watch():  # 서버 상태 변화를 지속적으로(server streaming) 감시하는 함수 정의
    with grpc.insecure_channel('localhost:50051') as channel:  # TLS 없이 localhost:50051 서버에 연결되는 채널 생성(with 블록 종료 시 자동 닫힘)
        stub = health_check_pb2_grpc.healthStub(channel)  # 채널을 이용해 health 서비스의 원격 메서드를 호출할 수 있는 스텁 생성
        responses = stub.Watch(health_check_pb2.HealthCheckRequest(service='my_service'))  # Watch 메서드를 호출하여 상태 응답을 연속으로 받는 스트림(이터레이터) 획득
        for response in responses:  # 서버가 보내는 상태 응답을 스트림에서 하나씩 반복 수신
            print(f"Health watch status for 'my_service': {response.status}")  # 수신할 때마다 현재 상태값(status) 출력

if __name__ == '__main__':
    print("Running health check...")
    run_check()
    print("\nRunning health watch...")
    run_watch()