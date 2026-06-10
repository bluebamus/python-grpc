from concurrent import futures  # ThreadPoolExecutor 제공: 여러 요청을 스레드 풀로 동시 처리

import grpc  # gRPC 핵심 라이브러리 (서버 생성 등)
import streaming_pb2  # protoc로 생성된 메시지 클래스 모듈 (Request/ResponseMessage)
import streaming_pb2_grpc  # protoc로 생성된 서비스 servicer/stub 모듈


class StreamingService(streaming_pb2_grpc.StreamingServiceServicer):  # 서비스 구현 클래스
    def StreamData(self, request_iterator, context):  # Client Streaming이므로 두 번째 인자는 요청 메시지들의 반복자(iterator)
        result = ""                                   # 누적 결과 문자열 초기화
        for req in request_iterator:                  # 클라이언트가 보낸 메시지를 하나씩 순회
            result += req.data + " "                  # 각 RequestMessage의 data 필드를 이어 붙임

        return streaming_pb2.ResponseMessage(result=result)  # 모든 요청 수신 후 단일 응답 1개 반환


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))           # gRPC 서버 생성, 최대 10개 스레드로 처리
    streaming_pb2_grpc.add_StreamingServiceServicer_to_server(StreamingService(), server)  # 구현체를 서버에 등록
    server.add_insecure_port('[::]:50051')            # 모든 인터페이스에서 포트 50051 수신 (암호화 없음)
    server.start()                                    # 서버 시작 (논블로킹)
    print("Server is running on port 50051...")
    server.wait_for_termination()                     # 서버가 종료될 때까지 대기


if __name__ == '__main__':                            # 스크립트가 직접 실행될 때만
    serve()                                           # 서버 실행
