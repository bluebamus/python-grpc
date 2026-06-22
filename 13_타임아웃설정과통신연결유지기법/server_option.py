import time  # Echo 처리 지연을 흉내 내기 위한 sleep 용도
from concurrent import futures  # 요청을 동시에 처리할 스레드 풀 제공

import grpc  # gRPC 서버 기능 제공
import wait_example_pb2  # wait_example.proto로 생성된 메시지 모듈
import wait_example_pb2_grpc  # wait_example.proto로 생성된 서비스 스텁/등록 함수 모듈

# ── keepalive(연결 유지) 서버 옵션 ──────────────────────────────
# 유휴 연결에서도 주기적으로 HTTP/2 PING을 주고받아 연결을 살아있게 유지하고,
# 죽은 연결을 빠르게 감지하기 위한 설정.
keep_alive_options = [
    ('grpc.keepalive_time_ms', 10000),                       # 활동이 없을 때 10초마다 ping 전송
    ('grpc.keepalive_timeout_ms', 5000),                     # ping 응답(ack)을 5초까지 대기, 없으면 끊김 처리
    ('grpc.keepalive_permit_without_calls', 1),              # 진행 중인 RPC가 없어도 ping 허용
    ('grpc.http2.min_ping_interval_without_data_ms', 5000),  # 클라가 5초보다 더 자주 ping하면 과도하다고 판단
]


class EchoServiceServicer(wait_example_pb2_grpc.EchoServiceServicer):
    def Echo(self, request, context):
        # 처리 시간이 걸리는 작업을 흉내 (타임아웃 예제와 동일하게 2초 지연)
        time.sleep(2)
        return wait_example_pb2.EchoResponse(message=request.message)


def serve():
    # grpc.server(...)의 options= 인자로 keepalive 옵션 리스트를 전달
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=keep_alive_options,
    )
    wait_example_pb2_grpc.add_EchoServiceServicer_to_server(EchoServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server (keepalive options) started on port 50051")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
