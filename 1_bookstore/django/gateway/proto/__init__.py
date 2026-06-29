"""컴파일된 protobuf 코드 패키지.

이 예제(1_bookstore)에는 gRPC 서비스가 없고 message 만 있다. 실제로 쓰는 것은
`book_pb2.py`(메시지 클래스) 뿐이다. 생성된 코드가 `import book_pb2` 처럼
최상위 임포트를 사용하므로, 이 디렉터리를 sys.path 에 등록해 임포트가
동작하게 한다.
"""

import sys
from pathlib import Path

_PROTO_DIR = str(Path(__file__).resolve().parent)
if _PROTO_DIR not in sys.path:
    sys.path.insert(0, _PROTO_DIR)
