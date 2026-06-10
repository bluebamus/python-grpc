import grpc                                            # gRPC 핵심 라이브러리 (채널 생성 등)
import streaming_pb2                                   # protoc로 생성된 메시지 클래스 모듈 (Request/ResponseMessage)
import streaming_pb2_grpc                              # protoc로 생성된 서비스 stub 모듈


def generate_requests():                              # 서버로 스트리밍할 요청들을 만드는 제너레이터
    messages = ["message 1", "message 2", "message 3"]  # 보낼 데이터 목록
    for msg in messages:                              # 하나씩 순회하며
        yield streaming_pb2.RequestMessage(data=msg)  # yield로 RequestMessage를 하나씩 스트리밍


def run():
    with grpc.insecure_channel('localhost:50051') as channel:  # 서버에 암호화 없는 채널 연결, with 종료 시 자동 close
        stub = streaming_pb2_grpc.StreamingServiceStub(channel)  # StreamingService 호출용 stub(클라이언트) 생성
        response = stub.StreamData(generate_requests())          # 요청 stream 전송 → 단일 응답 1개 수신
        print("Response from server:", response.result)          # 서버가 취합해 보낸 결과 출력


if __name__ == '__main__':                            # 스크립트가 직접 실행될 때만
    run()                                             # 클라이언트 실행
