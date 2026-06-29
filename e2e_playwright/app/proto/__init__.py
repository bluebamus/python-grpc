"""컴파일된 gRPC 코드 패키지.

생성된 `chat_pb2_grpc.py` 가 `import chat_pb2` 처럼 top-level 임포트를 쓰므로
이 디렉터리를 sys.path 에 등록한다.
"""

import sys
from pathlib import Path

_PROTO_DIR = str(Path(__file__).resolve().parent)
if _PROTO_DIR not in sys.path:
    sys.path.insert(0, _PROTO_DIR)
