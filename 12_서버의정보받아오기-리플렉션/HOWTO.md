# 서버의 정보 받아오기 — gRPC 서버 리플렉션(Server Reflection) HOWTO

gRPC **서버 리플렉션**은 클라이언트가 `.proto` 파일을 미리 갖고 있지 않아도, 서버에 **어떤 서비스/메서드/메시지가 있는지** 실시간으로 물어볼 수 있게 해주는 기능입니다. `grpcurl` 같은 디버깅 도구나 동적 클라이언트가 이 기능을 사용합니다.

이 폴더는 `EchoService` 서버에 리플렉션을 활성화하고, 파이썬 클라이언트와 `grpcurl`로 서비스 목록을 조회하는 예제입니다.

> 📌 이 문서는 **gRPC를 처음 배우는 분**을 위해 한 단계씩 자세히 설명합니다. 4번 "실행 방법"으로 먼저 돌려보고, 6번 "클라이언트 코드 한 줄씩 이해하기"로 원리를 익히는 순서를 추천합니다.

---

## 1. 폴더 구성

| 파일 | 설명 |
|---|---|
| `reflection_example.proto` | `EchoService` 정의(원본 proto) |
| `reflection_example_pb2.py` | proto로 생성된 메시지 코드 |
| `reflection_example_pb2_grpc.py` | proto로 생성된 서비스 스텁/서버 코드 |
| `server.py` | 리플렉션을 활성화한 Echo 서버 |
| `reflection_client.py` | 리플렉션으로 서비스 목록을 조회하는 파이썬 클라이언트 |
| `grpcurl.exe` | 리플렉션 기반 CLI 디버깅 도구(Windows) |
| `install-grpcurl.txt` | grpcurl 설치 안내 |

---

## 2. 사전 준비

프로젝트 루트에서 의존성을 설치합니다(이미 `pyproject.toml`에 포함됨).

```bash
# 프로젝트 루트(F:\project\grpc\python-grpc)에서
uv sync
```

필요한 패키지: `grpcio`, `grpcio-reflection`, `grpcio-tools`.

---

## 3. proto 코드 재생성(수정했을 때만)

`reflection_example.proto`를 수정한 경우, **이 폴더 안에서** 아래 명령으로 다시 생성합니다.

```bash
cd 12_서버의정보받아오기-리플렉션
uv run python -m grpc_tools.protoc -I=. --python_out=. --grpc_python_out=. reflection_example.proto
```

> ⚠️ 생성된 `*_pb2_grpc.py`는 `import reflection_example_pb2`처럼 **파일명 그대로 import**하므로, proto 파일명·import 이름·실제 파일명이 모두 일치해야 합니다.

---

## 4. 실행 방법

### 4-1. 서버 실행

```bash
cd 12_서버의정보받아오기-리플렉션
uv run python server.py
```

출력:

```
Server is running on port 50051...
```

> 서버는 `localhost:50051`에서 대기합니다. 종료하려면 `Ctrl + C`.

### 4-2. 파이썬 클라이언트로 서비스 목록 조회

**다른 터미널**에서:

```bash
cd 12_서버의정보받아오기-리플렉션
uv run python reflection_client.py
```

기대 출력:

```
Running reflection client...
Service: grpc.reflection.v1alpha.ServerReflection
Service: reflection_example.EchoService
```

- `grpc.reflection.v1alpha.ServerReflection` — 리플렉션 서비스 자체
- `reflection_example.EchoService` — 우리가 만든 Echo 서비스

---

## 5. grpcurl로 조회(선택)

`grpcurl`은 proto 없이도 리플렉션으로 서버를 탐색할 수 있는 CLI입니다. (설치는 `install-grpcurl.txt` 참고)

```bash
# 서비스 목록
./grpcurl.exe -plaintext localhost:50051 list

# EchoService의 메서드 목록
./grpcurl.exe -plaintext localhost:50051 list reflection_example.EchoService

# Echo 메서드 호출
./grpcurl.exe -plaintext -d '{\"message\": \"hello\"}' localhost:50051 reflection_example.EchoService/Echo
```

> `-plaintext`는 TLS 없이 평문으로 통신한다는 의미입니다(서버가 `insecure_port`로 열려 있으므로 필요).

---

## 6. 클라이언트 코드 한 줄씩 이해하기 (`reflection_client.py`)

아래는 우리 예제의 클라이언트 전체 코드입니다. 이어서 **블록별로** 무슨 일이 일어나는지 초보자 눈높이로 설명합니다.

```python
import grpc
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc


def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = reflection_pb2_grpc.ServerReflectionStub(channel)

        request = reflection_pb2.ServerReflectionRequest(
            list_services="*"
        )

        response = stub.ServerReflectionInfo(iter([request]))
        for service in response:
            for service_response in service.list_services_response.service:
                print(f"Service: {service_response.name}")

if __name__ == '__main__':
    print("Running reflection client...")
    run()
```

### ① import — 무엇을 불러오는가

```python
import grpc
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc
```

- `grpc` : 서버에 연결하는 통로(채널)를 만드는 핵심 라이브러리입니다.
- `reflection_pb2` : **리플렉션 요청/응답 메시지**의 설계도입니다. 여기서 `ServerReflectionRequest`(요청)를 만듭니다.
- `reflection_pb2_grpc` : 리플렉션 서비스를 **원격으로 호출**하기 위한 도구(`ServerReflectionStub`)가 들어 있습니다.

> 💡 이 두 모듈은 우리가 만든 게 아니라 `grpcio-reflection` 패키지가 기본 제공합니다. 그래서 별도 proto 없이 바로 import할 수 있습니다.

### ② 채널 만들기 — "호스트 필드"

```python
with grpc.insecure_channel('localhost:50051') as channel:
```

여기서 `'localhost:50051'` 이 바로 **호스트(주소) 필드**입니다. 형식은 `호스트:포트`입니다.

| 부분 | 의미 |
|---|---|
| `localhost` | 접속할 서버의 **주소(호스트)**. `localhost`는 "내 컴퓨터 자신"을 뜻합니다. 다른 PC에 붙으려면 `192.168.0.10` 같은 IP나 도메인으로 바꿉니다. |
| `50051` | 서버가 열어 둔 **포트 번호**. `server.py`의 `add_insecure_port('[::]:50051')`와 **반드시 같아야** 연결됩니다. |

- `insecure_channel` 의 *insecure*는 **TLS(암호화) 없이 평문으로 연결**한다는 뜻입니다. 학습/로컬 테스트용이며, 실제 서비스에서는 `secure_channel`(TLS)을 씁니다.
- `with ... as channel:` 구문을 쓰면 블록이 끝날 때 **채널이 자동으로 닫혀** 자원 누수를 막아 줍니다.

> ✅ 자주 하는 실수: 서버 포트와 클라이언트 포트가 다르거나, 서버를 켜지 않은 채 클라이언트를 실행하면 `StatusCode.UNAVAILABLE`(연결 실패)이 납니다.

### ③ 스텁(stub) 만들기 — 원격 호출용 리모컨

```python
stub = reflection_pb2_grpc.ServerReflectionStub(channel)
```

- **스텁**은 "원격 서버의 메서드를 내 함수처럼 부르게 해주는 리모컨"이라고 생각하면 쉽습니다.
- 위에서 만든 `channel`(연결 통로)을 넣어 만듭니다. 이제 `stub.ServerReflectionInfo(...)`처럼 서버 기능을 호출할 수 있습니다.

### ④ 요청 메시지 만들기 — "list_services 필드"

```python
request = reflection_pb2.ServerReflectionRequest(
    list_services="*"
)
```

`ServerReflectionRequest`는 "서버에게 무엇을 물어볼지" 담는 요청 메시지입니다. 이 중 **`list_services` 필드**는 **"네가 가진 서비스 목록을 전부 알려줘"** 라는 의미의 질문입니다.

- 값으로 넣는 **`"*"`** 는 "모든 서비스"를 뜻하는 관례적인 표시입니다. (`grpcurl`도 동일하게 `*`를 사용)
- 참고로 `list_services`는 `ServerReflectionRequest` 안의 **여러 질문 종류 중 하나**입니다. 리플렉션은 이 외에도 아래 같은 질문을 할 수 있습니다.

| 요청 필드 | 무엇을 물어보는가 |
|---|---|
| `list_services` | 서버가 가진 **서비스 목록** (이 예제에서 사용) |
| `file_by_filename` | 특정 `.proto` **파일 이름**으로 정의 내용 조회 |
| `file_containing_symbol` | 특정 **심볼(서비스/메시지 이름)**이 들어 있는 proto 정의 조회 |

> 💡 `list_services`에 빈 문자열 `""`을 넣어도 동작하지만, 의미가 분명하도록 **`"*"`를 쓰는 것이 표준 권장**입니다.

### ⑤ 요청 보내고 응답 받기 — 양방향 스트리밍

```python
response = stub.ServerReflectionInfo(iter([request]))
```

- 리플렉션 호출(`ServerReflectionInfo`)은 **양방향 스트리밍 RPC**입니다. 즉, 클라이언트가 요청을 **여러 개 연달아** 보낼 수 있고, 서버도 응답을 **여러 개 연달아** 돌려줍니다.
- 그래서 요청 하나를 보내더라도 **이터레이터(스트림) 형태**로 감싸야 합니다 → `iter([request])` 는 "요청 1개짜리 스트림"을 만든 것입니다.
- 반환값 `response`도 한 번에 끝나는 값이 아니라 **응답들이 흘러나오는 스트림**입니다.

### ⑥ 응답 순회하며 서비스 이름 출력

```python
for service in response:
    for service_response in service.list_services_response.service:
        print(f"Service: {service_response.name}")
```

- 바깥 `for` : 서버가 보낸 응답(`ServerReflectionResponse`)을 **하나씩** 꺼냅니다.
- `service.list_services_response.service` : 응답 안에는 서비스 목록이 **리스트(반복 필드)**로 들어 있습니다. 안쪽 `for`로 그 리스트를 하나씩 돕니다.
- `service_response.name` : 각 서비스의 **전체 이름(full name)** 입니다. 이걸 출력합니다.

실행하면 다음처럼 출력됩니다.

```
Service: grpc.reflection.v1alpha.ServerReflection
Service: reflection_example.EchoService
```

> 변수 이름(`service`, `service_response`)이 헷갈릴 수 있는데, **바깥 = 응답 1건**, **안쪽 = 그 응답에 담긴 서비스 1개**라고 기억하면 됩니다.

### ⑦ 진입점

```python
if __name__ == '__main__':
    print("Running reflection client...")
    run()
```

- 이 파일을 `python reflection_client.py`로 **직접 실행할 때만** `run()`이 호출됩니다.
- 다른 파일에서 `import` 했을 때는 자동 실행되지 않도록 막아 주는, 파이썬의 표준 관용구입니다.

---

## 7. 동작 원리 요약

1. **서버**(`server.py`)는 `reflection.enable_server_reflection(SERVICE_NAMES, server)`로 노출할 서비스 이름들을 등록합니다.
   - `EchoService`의 전체 이름과 리플렉션 서비스(`reflection.SERVICE_NAME`)를 함께 등록해야 클라이언트가 리플렉션을 쓸 수 있습니다.
2. **클라이언트**(`reflection_client.py`)는 `ServerReflectionStub`으로 `list_services="*"` 요청을 보내고, 응답 스트림에서 서비스 목록을 받아 출력합니다.
   - 리플렉션 RPC(`ServerReflectionInfo`)는 **양방향 스트리밍**이라 요청을 이터레이터(`iter([request])`)로 전달합니다.

---

## 8. 자주 발생하는 오류

| 증상 | 원인 | 해결 |
|---|---|---|
| `ModuleNotFoundError: No module named 'reflection_example_pb2'` | proto 생성물 파일명과 `server.py`의 import 이름 불일치 | 파일명/ import 이름을 일치시키고 재생성(3번) |
| `ModuleNotFoundError: No module named 'grpc_reflection'` | `grpcio-reflection` 미설치 | `uv sync` 또는 `uv add grpcio-reflection` |
| 클라이언트 `failed to connect` / `StatusCode.UNAVAILABLE` | 서버 미실행 또는 포트 불일치 | 서버를 먼저 실행하고 `localhost:50051` 확인 |
| `import` 실패(상대 경로) | 다른 폴더에서 실행 | 반드시 이 폴더 안(`cd`)에서 실행 |
