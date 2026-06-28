from concurrent import futures

import example_pb2
import example_pb2_grpc
import grpc


class ExampleServiceServicer(example_pb2_grpc.ExampleServiceServicer):
    def SayHello(self, request, context):
        response = example_pb2.HelloReply()
        response.message = f"Hello, {request.name}!"
        return response
    

def serve():
    # Load server certificate and private key
    with open('server.key', 'rb') as f:
        private_key = f.read()
    with open('server.crt', 'rb') as f:
        certificate_chain = f.read()
    
    server_credentials = grpc.ssl_server_credentials(((private_key, certificate_chain),))


    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    example_pb2_grpc.add_ExampleServiceServicer_to_server(ExampleServiceServicer(), server)
    server.add_secure_port('[::]:50051', server_credentials)

    server.start()
    print("Server started on port 50051 with TLS.")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()