"""컴파일된 protobuf 코드 패키지.

이 예제(1_bookstore)에는 gRPC 서비스가 없고 message 만 있다. 따라서
실제로 쓰는 것은 `book_pb2.py`(메시지 클래스) 뿐이며, `book_pb2_grpc.py`
는 서비스가 없어 사실상 비어 있다.

protoc가 생성한 코드는 내부에서 `import book_pb2` 처럼 최상위(top-level)
임포트를 사용한다. 이 디렉터리를 sys.path에 추가해야 그 임포트가 동작하므로,
패키지 로드 시점에 자기 경로를 등록한다.
"""

import sys
from pathlib import Path

_PROTO_DIR = str(Path(__file__).resolve().parent)
if _PROTO_DIR not in sys.path:
    sys.path.insert(0, _PROTO_DIR)
