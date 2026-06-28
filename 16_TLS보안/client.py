import example_pb2
import example_pb2_grpc
import grpc


def run():
    with open('server.crt', 'rb') as f:
        trusted_certs = f.read()

    credentials = grpc.ssl_channel_credentials(root_certificates=trusted_certs)
    channel = grpc.secure_channel('localhost:50051', credentials)
    stub = example_pb2_grpc.ExampleServiceStub(channel)
    response = stub.SayHello(example_pb2.HelloRequest(name='World'))
    print("Client received: " + response.message)


if __name__ == '__main__':
    run()