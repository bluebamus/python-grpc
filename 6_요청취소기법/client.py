import time

import cancel_example_pb2
import cancel_example_pb2_grpc
import grpc


def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = cancel_example_pb2_grpc.CancelServiceStub(channel)
        request = cancel_example_pb2.Request(request_data="Start long operation")

        # Start the long-running operation in a separate thread
        future = stub.LongRunningOperation.future(request)

        # Wait for a few seconds before cancelling
        time.sleep(3)
        print("Cancelling the request...")
        future.cancel()

        try:
            response = future.result()
            print(f"Response from server: {response.response_data}")
        except grpc.FutureCancelledError:
            print("The request was cancelled successfully.")


if __name__ == '__main__':
    run()