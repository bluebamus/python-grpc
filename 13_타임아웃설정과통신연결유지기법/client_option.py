import sys  # 표준출력 인코딩 설정용
import time  # 유휴 구간(idle)을 만들기 위한 sleep 용도

# Windows 콘솔(cp949)에서도 한글/이모지가 깨지거나 오류 나지 않도록 UTF-8로 출력
sys.stdout.reconfigure(encoding='utf-8')

import grpc  # gRPC 클라이언트/채널 기능 제공
import wait_example_pb2  # wait_example.proto로 생성된 메시지 모듈
import wait_example_pb2_grpc  # wait_example.proto로 생성된 스텁 모듈

# ── keepalive(연결 유지) 클라이언트 옵션 ────────────────────────
# 서버 옵션과 호환되도록 ping 주기를 맞춘다.
#  - 클라 keepalive_time_ms(10초) >= 서버 min_ping_interval_without_data_ms(5초) 이므로
#    'too_many_pings'로 끊기지 않는다.
keep_alive_options = [
    ('grpc.keepalive_time_ms', 10000),             # 활동이 없을 때 10초마다 ping 전송
    ('grpc.keepalive_timeout_ms', 5000),           # ping 응답을 5초까지 대기
    ('grpc.keepalive_permit_without_calls', 1),    # RPC가 없어도 ping 허용
    ('grpc.http2.max_pings_without_data', 0),      # 데이터 없이 보낼 ping 횟수 제한 해제(0=무제한)
]


def run():
    # 채널 생성 시 options=로 keepalive 옵션 전달
    with grpc.insecure_channel('localhost:50051', options=keep_alive_options) as channel:
        stub = wait_example_pb2_grpc.EchoServiceStub(channel)

        # 1차 호출: 연결을 맺고 정상 응답 확인 (서버가 2초 지연하므로 timeout=10으로 여유)
        resp1 = stub.Echo(wait_example_pb2.EchoRequest(message='first call'), timeout=10)
        print("1st response:", resp1.message)

        # 유휴 구간: 이 동안 아무 RPC도 없지만 keepalive ping이 오가며 연결이 유지된다.
        print("Idle for 15s (keepalive ping이 오가며 연결을 유지)...")
        time.sleep(15)

        # 2차 호출: 같은 채널(연결)이 끊기지 않고 재사용되는지 확인
        resp2 = stub.Echo(wait_example_pb2.EchoRequest(message='second call'), timeout=10)
        print("2nd response:", resp2.message)

        print("OK: 유휴 구간 이후에도 연결이 유지되어 재호출 성공 ✅")


if __name__ == '__main__':
    run()
