import grpc
import metadata_example_pb2
import metadata_example_pb2_grpc


def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = metadata_example_pb2_grpc.EchoServiceStub(channel)

        # Create metadata to send with the request
        metadata = (('client-metadata-key', 'client-metadata-value'),)

        response, call = stub.Echo.with_call(metadata_example_pb2.EchoRequest(message='Hello, gRPC!'), metadata=metadata)

        print("Received response:", response.message)

        server_metadata = dict(call.trailing_metadata())
        print("Received server metadata:", server_metadata)


if __name__ == '__main__':
    run()