import error_handling_example_pb2
import error_handling_example_pb2_grpc
import grpc


def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = error_handling_example_pb2_grpc.CalculatorStub(channel)
        try:
            response = stub.Divide(error_handling_example_pb2.DivideRequest(dividend=10, divisor=2))
            print(f"Quotient: {response.quotient}")
        except grpc.RpcError as e:
            print(f"RPC failed with status code {e.code()}: {e.details()}")


if __name__ == '__main__':
    run()