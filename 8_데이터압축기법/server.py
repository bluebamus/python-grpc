from concurrent import futures

import example_pb2
import example_pb2_grpc
import grpc


class DataServiceServicer(example_pb2_grpc.DataServiceServicer):
    def GetData(self, request, context):
        # 요청에서 데이터 가져오기
        data = b"This is ad large data example."*10000

        print(f"Original data size: {len(data)} bytes")
        # 응답 생성
        return example_pb2.DataResponse(data=data)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),compression=grpc.Compression.Gzip)
    example_pb2_grpc.add_DataServiceServicer_to_server(DataServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    print("Server is running on port 50051...")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
    