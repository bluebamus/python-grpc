import time  # Watch 스트림에서 일정 간격(초)으로 대기하기 위한 표준 라이브러리
from concurrent import futures  # gRPC 서버가 요청을 동시에 처리할 스레드 풀(ThreadPoolExecutor)을 제공

import grpc  # gRPC 서버/채널 기능을 제공하는 핵심 라이브러리
import health_check_pb2  # health_check.proto로 생성한 메시지(HealthCheckRequest/Response) 모듈
import health_check_pb2_grpc  # health_check.proto로 생성한 서비스 스텁/서버 등록 함수 모듈
from health_check_pb2 import HealthCheckResponse  # 상태 enum(SERVING 등)과 응답 메시지 타입


class HealthCheck(health_check_pb2_grpc.healthServicer):  # 생성된 healthServicer를 상속받아 헬스체크 로직을 직접 구현하는 클래스
    def __init__(self):  # 인스턴스 생성 시 서비스별 상태 정보를 초기화
        self.status_map={  # 서비스 이름 → 상태값을 매핑하는 딕셔너리
            "": HealthCheckResponse.SERVING,  # 빈 문자열("")은 서버 전체 상태를 의미하며 SERVING(정상)으로 설정
            "my_service": HealthCheckResponse.SERVING  # 'my_service'의 상태를 SERVING(정상)으로 설정
        }

    def Check(self, request, context):  # 클라이언트의 1회성 상태 조회 요청을 처리하는 메서드
        status = self.status_map.get(request.service, HealthCheckResponse.SERVICE_UNKNOWN)  # 요청한 서비스의 상태를 조회, 없으면 SERVICE_UNKNOWN 반환
        return health_check_pb2.HealthCheckResponse(status=status)  # 조회한 상태값을 담은 응답 메시지를 반환

    def Watch(self, request, context):  # 클라이언트에게 상태를 스트림으로 계속 전송하는 메서드
        while True:  # 연결이 유지되는 동안 무한 반복하며 상태를 주기적으로 전송
            status = self.status_map.get(request.service, HealthCheckResponse.SERVICE_UNKNOWN)  # 요청한 서비스의 현재 상태를 조회, 없으면 SERVICE_UNKNOWN
            yield health_check_pb2.HealthCheckResponse(status=status)  # 상태값을 담은 응답을 스트림으로 하나씩 전송(yield)
            time.sleep(5) # 다음 상태 업데이트를 보내기 전 5초간 대기

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    health_servicer = HealthCheck()
    health_check_pb2_grpc.add_healthServicer_to_server(health_servicer, server)
    server.add_insecure_port('[::]:50051')
    print("Health check server is running on port 50051...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()