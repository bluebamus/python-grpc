# FastAPI / Django에서 grpcurl(리플렉션) 사용하기 — 설계 가이드

`grpcurl`은 **gRPC 서버 리플렉션**을 이용해 `.proto` 파일 없이도 서버를 탐색·호출하는 **CLI 디버깅 도구**입니다. (이 폴더 `12_서버의정보받아오기-리플렉션`의 `HOWTO.md` 참고)

학습 예제에서는 터미널에서 `grpcurl.exe ... list` 같은 명령을 직접 입력했습니다. 하지만 **FastAPI·Django 같은 웹 서버 안에서 터미널 명령(grpcurl)을 실행하는 것은 좋은 설계가 아닙니다.** 이 문서는 그 이유와, 같은 일을 **코드로 올바르게 구현하는 방법**을 단계별로 설명합니다.

> 📌 한 줄 요약: `grpcurl`이 하는 일(리플렉션으로 서비스 조회 + 동적 호출)은 전부 **파이썬 gRPC 라이브러리로 직접** 할 수 있습니다. 웹 앱에서는 외부 CLI를 호출하지 말고 **리플렉션 API**를 쓰세요.

---

## 목차

1. [왜 웹 서버에서 grpcurl을 직접 호출하면 안 되는가](#1-왜-웹-서버에서-grpcurl을-직접-호출하면-안-되는가)
2. [핵심 개념: grpcurl = 리플렉션 + 동적 호출](#2-핵심-개념-grpcurl--리플렉션--동적-호출)
3. [세 가지 접근 방식 비교](#3-세-가지-접근-방식-비교)
4. [공통 모듈: 리플렉션 기반 동적 gRPC 클라이언트](#4-공통-모듈-리플렉션-기반-동적-grpc-클라이언트)
5. [FastAPI 적용](#5-fastapi-적용)
6. [Django 적용](#6-django-적용)
7. [추천: 운영 환경에서는 stub을 미리 생성](#7-추천-운영-환경에서는-stub을-미리-생성)
8. [안티패턴: subprocess로 grpcurl 실행 (피하세요)](#8-안티패턴-subprocess로-grpcurl-실행-피하세요)
9. [자주 발생하는 오류](#9-자주-발생하는-오류)

---

## 1. 왜 웹 서버에서 grpcurl을 직접 호출하면 안 되는가

터미널에서 `grpcurl`을 치는 것과, FastAPI/Django **요청 처리 중에** `grpcurl`을 실행(`subprocess`)하는 것은 전혀 다릅니다. 후자는 다음 문제가 있습니다.

| 문제 | 설명 |
|---|---|
| **성능** | 요청마다 새 **프로세스를 fork** → CPU·메모리 낭비, 지연 증가. gRPC의 장점인 커넥션 재사용이 사라집니다. |
| **취약한 파싱** | grpcurl의 **표준출력(텍스트/JSON)을 문자열로 파싱**해야 함. 출력 형식이 바뀌면 깨집니다. |
| **에러 처리 불가** | gRPC 상태 코드(`UNAVAILABLE`, `NOT_FOUND` 등)를 구조적으로 다루기 어렵고, exit code·stderr 텍스트에 의존하게 됩니다. |
| **보안(명령어 주입)** | 사용자 입력을 grpcurl 인자로 넘기면 **셸 인젝션** 위험. |
| **배포 복잡도** | 컨테이너/서버마다 `grpcurl` 바이너리를 별도 설치·관리해야 합니다. |
| **관측성 부족** | 메트릭·트레이싱·타임아웃·재시도 같은 gRPC 클라이언트 기능을 못 씁니다. |

> ✅ 결론: grpcurl은 **사람이 손으로 디버깅할 때 쓰는 도구**입니다. 애플리케이션 코드 안에서는 **gRPC 라이브러리 API**를 직접 사용하세요.

---

## 2. 핵심 개념: grpcurl = 리플렉션 + 동적 호출

`grpcurl localhost:50051 list` 명령이 내부에서 하는 일은 사실 단순합니다.

1. 서버의 **리플렉션 서비스**(`grpc.reflection.v1alpha.ServerReflection`)에 접속한다.
2. "어떤 서비스/메서드/메시지가 있냐"고 물어 **proto 정의(디스크립터)** 를 받아온다.
3. 받은 디스크립터로 **요청 메시지를 동적으로 만들어** 서버 메서드를 호출한다.

이 3단계는 모두 파이썬으로 그대로 구현할 수 있습니다.

- 1·2단계 → `grpc_reflection` 패키지 (`reflection_client.py`에서 이미 1·2를 맛봤습니다)
- 3단계 → `google.protobuf`의 **DescriptorPool + 메시지 팩토리 + 제네릭 채널 호출**

즉, **별도 proto 파일이 없어도** grpcurl처럼 "조회하고 호출"할 수 있습니다.

---

## 3. 세 가지 접근 방식 비교

| 방식 | 언제 쓰나 | 장점 | 단점 |
|---|---|---|---|
| **A. 미리 생성한 stub 사용** (7장) | 호출할 서비스의 `.proto`를 안다 (대부분의 운영) | 타입 안전, 가장 빠름, 단순 | 빌드 시 proto 코드 생성 필요 |
| **B. 리플렉션 동적 클라이언트** (4~6장) | proto 없이 임의 서버를 탐색/호출 (어드민·게이트웨이·디버그 UI) | proto 불필요, grpcurl과 동일한 유연성 | 코드 복잡, 런타임 의존, 타입 안전 약함 |
| **C. subprocess로 grpcurl 실행** (8장) | ❌ 권장하지 않음 | 빠른 임시 방편 | 위 1장의 모든 문제 |

> 💡 운영 서비스의 일반 호출은 **A**, "grpcurl을 웹으로 옮기고 싶다"(관리자 콘솔/동적 게이트웨이)면 **B**를 쓰세요. **C는 피하세요.**

---

## 4. 공통 모듈: 리플렉션 기반 동적 gRPC 클라이언트

먼저 FastAPI·Django가 공유할 **순수 파이썬 동적 클라이언트**를 만듭니다. 이게 grpcurl의 핵심 기능(`list`, `describe`, 메서드 호출)을 코드로 옮긴 것입니다.

> 필요 패키지: `grpcio`, `grpcio-reflection`, `protobuf` (이 프로젝트는 `uv sync`로 설치됨)

`grpc_reflection_client.py`:

```python
"""리플렉션으로 gRPC 서버를 탐색/호출하는 동적 클라이언트.

grpcurl의 list / describe / 메서드 호출을 순수 파이썬으로 구현한다.
proto 파일이 없어도 서버 리플렉션만 켜져 있으면 동작한다.
"""
import grpc
from google.protobuf.descriptor_pool import DescriptorPool
from google.protobuf.json_format import MessageToDict, ParseDict
from grpc_reflection.v1alpha.proto_reflection_descriptor_database import (
    ProtoReflectionDescriptorDatabase,
)

try:
    # protobuf >= 4.22 권장 API
    from google.protobuf.message_factory import GetMessageClass

    def _message_class(descriptor):
        return GetMessageClass(descriptor)
except ImportError:  # 구버전 protobuf 호환
    from google.protobuf.message_factory import MessageFactory

    _factory = MessageFactory()

    def _message_class(descriptor):
        return _factory.GetPrototype(descriptor)


class GrpcReflectionClient:
    """하나의 gRPC 서버 주소에 대한 동적 클라이언트."""

    def __init__(self, target: str):
        # 학습용이라 평문(insecure). 운영에서는 grpc.secure_channel + TLS 사용.
        self._channel = grpc.insecure_channel(target)
        self._db = ProtoReflectionDescriptorDatabase(self._channel)
        self._pool = DescriptorPool(self._db)

    def close(self):
        self._channel.close()

    # with 문 지원 (자원 자동 정리)
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ── grpcurl list ─────────────────────────────────────────────
    def list_services(self) -> list[str]:
        """서버가 노출하는 서비스 전체 이름 목록. (grpcurl ... list)"""
        return list(self._db.get_services())

    def list_methods(self, service_name: str) -> list[str]:
        """특정 서비스의 메서드 이름 목록. (grpcurl ... list <svc>)"""
        service = self._pool.FindServiceByName(service_name)
        return [m.name for m in service.methods]

    # ── grpcurl describe ─────────────────────────────────────────
    def describe_method(self, service_name: str, method_name: str) -> dict:
        """메서드의 입력/출력 메시지 타입을 설명. (grpcurl ... describe)"""
        service = self._pool.FindServiceByName(service_name)
        method = service.FindMethodByName(method_name)
        return {
            "name": method.full_name,
            "input_type": method.input_type.full_name,
            "output_type": method.output_type.full_name,
            "client_streaming": method.client_streaming,
            "server_streaming": method.server_streaming,
        }

    # ── grpcurl -d '{...}' <svc>/<method> (unary 호출) ───────────
    def call_unary(self, service_name: str, method_name: str, payload: dict) -> dict:
        """JSON 페이로드로 unary 메서드를 호출하고 응답을 dict로 반환.

        grpcurl -d '{"message":"hi"}' host svc/Method 와 동일한 동작.
        """
        service = self._pool.FindServiceByName(service_name)
        method = service.FindMethodByName(method_name)
        if method.client_streaming or method.server_streaming:
            raise ValueError("이 헬퍼는 unary-unary 메서드만 지원합니다.")

        request_cls = _message_class(method.input_type)
        response_cls = _message_class(method.output_type)

        # dict(JSON) → protobuf 메시지
        request_msg = ParseDict(payload, request_cls())

        # 제네릭 채널 호출 (stub 없이 메서드 경로를 직접 지정)
        rpc = self._channel.unary_unary(
            f"/{service_name}/{method_name}",
            request_serializer=request_cls.SerializeToString,
            response_deserializer=response_cls.FromString,
        )
        response_msg = rpc(request_msg)

        # protobuf 메시지 → dict(JSON)
        return MessageToDict(response_msg, preserving_proto_field_name=True)
```

### 이 모듈이 grpcurl 명령에 대응되는 표

| grpcurl 명령 | 이 모듈 메서드 |
|---|---|
| `grpcurl -plaintext localhost:50051 list` | `list_services()` |
| `grpcurl -plaintext localhost:50051 list reflection_example.EchoService` | `list_methods("reflection_example.EchoService")` |
| `grpcurl ... describe reflection_example.EchoService.Echo` | `describe_method("reflection_example.EchoService", "Echo")` |
| `grpcurl -d '{"message":"hi"}' ... reflection_example.EchoService/Echo` | `call_unary("reflection_example.EchoService", "Echo", {"message": "hi"})` |

---

## 5. FastAPI 적용

FastAPI에서는 위 동적 클라이언트를 **REST 엔드포인트로 감싸서** "웹에서 쓰는 grpcurl"을 만들 수 있습니다.

> ⚠️ `ProtoReflectionDescriptorDatabase`는 **동기(blocking)** 호출입니다. FastAPI의 비동기 이벤트 루프를 막지 않도록, gRPC 작업은 `run_in_threadpool`로 스레드에서 실행합니다.

`main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from grpc_reflection_client import GrpcReflectionClient

GRPC_TARGET = "localhost:50051"  # 호출 대상 gRPC 서버


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 채널 1개를 만들어 재사용 (요청마다 새로 만들지 않음)
    app.state.grpc = GrpcReflectionClient(GRPC_TARGET)
    yield
    app.state.grpc.close()


app = FastAPI(lifespan=lifespan)


class CallRequest(BaseModel):
    payload: dict


# grpcurl list  →  GET /grpc/services
@app.get("/grpc/services")
async def list_services():
    client: GrpcReflectionClient = app.state.grpc
    services = await run_in_threadpool(client.list_services)
    return {"services": services}


# grpcurl list <svc>  →  GET /grpc/services/{service}/methods
@app.get("/grpc/services/{service}/methods")
async def list_methods(service: str):
    client: GrpcReflectionClient = app.state.grpc
    try:
        methods = await run_in_threadpool(client.list_methods, service)
    except KeyError:
        raise HTTPException(404, f"service not found: {service}")
    return {"service": service, "methods": methods}


# grpcurl -d '{...}' <svc>/<method>  →  POST /grpc/{service}/{method}
@app.post("/grpc/{service}/{method}")
async def call_method(service: str, method: str, body: CallRequest):
    client: GrpcReflectionClient = app.state.grpc
    try:
        result = await run_in_threadpool(
            client.call_unary, service, method, body.payload
        )
    except grpc.RpcError as e:  # type: ignore  # 아래 import 참고
        raise HTTPException(502, f"gRPC error: {e.code().name}: {e.details()}")
    return {"response": result}
```

> 위 코드 상단에 `import grpc` 를 추가하세요(RpcError 처리용).

**사용 예 (터미널 명령 대신 HTTP 요청):**

```bash
# 학습 예제에서: grpcurl -plaintext localhost:50051 list
curl http://localhost:8000/grpc/services

# grpcurl -plaintext localhost:50051 list reflection_example.EchoService
curl http://localhost:8000/grpc/services/reflection_example.EchoService/methods

# grpcurl -d '{"message":"hello"}' ... reflection_example.EchoService/Echo
curl -X POST http://localhost:8000/grpc/reflection_example.EchoService/Echo \
     -H "Content-Type: application/json" \
     -d '{"payload": {"message": "hello"}}'
```

이제 grpcurl을 터미널에서 칠 필요 없이, **FastAPI가 리플렉션을 대신 수행**합니다.

---

## 6. Django 적용

Django에서는 두 가지 위치에서 쓸 수 있습니다.

### 6-1. 뷰(View)에서 — 웹 API로 노출

`grpc_proxy/views.py`:

```python
import json

import grpc
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from grpc_reflection_client import GrpcReflectionClient

GRPC_TARGET = "localhost:50051"


# grpcurl list
@require_http_methods(["GET"])
def list_services(request):
    with GrpcReflectionClient(GRPC_TARGET) as client:
        return JsonResponse({"services": client.list_services()})


# grpcurl list <svc>
@require_http_methods(["GET"])
def list_methods(request, service):
    with GrpcReflectionClient(GRPC_TARGET) as client:
        try:
            methods = client.list_methods(service)
        except KeyError:
            return JsonResponse({"error": f"service not found: {service}"}, status=404)
    return JsonResponse({"service": service, "methods": methods})


# grpcurl -d '{...}' <svc>/<method>
@csrf_exempt  # 실제 서비스에서는 적절한 인증/CSRF 정책을 적용하세요.
@require_http_methods(["POST"])
def call_method(request, service, method):
    payload = json.loads(request.body or "{}").get("payload", {})
    with GrpcReflectionClient(GRPC_TARGET) as client:
        try:
            result = client.call_unary(service, method, payload)
        except grpc.RpcError as e:
            return JsonResponse(
                {"error": f"{e.code().name}: {e.details()}"}, status=502
            )
    return JsonResponse({"response": result})
```

`grpc_proxy/urls.py`:

```python
from django.urls import path

from . import views

urlpatterns = [
    path("grpc/services", views.list_services),
    path("grpc/services/<str:service>/methods", views.list_methods),
    path("grpc/<str:service>/<str:method>", views.call_method),
]
```

> 💡 위 뷰는 요청마다 채널을 새로 엽니다(간단함 우선). 트래픽이 많으면 **채널을 모듈 전역으로 1개 만들어 재사용**하거나, 앱 `ready()`에서 초기화해 캐싱하세요.

### 6-2. management 명령에서 — "코드로 된 grpcurl"

운영/CI 스크립트에서 터미널 grpcurl 대신 Django 명령으로 조회할 수 있습니다.

`grpc_proxy/management/commands/grpc_list.py`:

```python
from django.core.management.base import BaseCommand

from grpc_reflection_client import GrpcReflectionClient


class Command(BaseCommand):
    help = "리플렉션으로 gRPC 서버의 서비스 목록을 출력 (grpcurl list 대체)"

    def add_arguments(self, parser):
        parser.add_argument("--target", default="localhost:50051")

    def handle(self, *args, **opts):
        with GrpcReflectionClient(opts["target"]) as client:
            for name in client.list_services():
                self.stdout.write(name)
```

실행: `python manage.py grpc_list --target localhost:50051`
→ 외부 grpcurl 바이너리 없이, **프로젝트 코드 안에서** 동일 결과를 얻습니다.

---

## 7. 추천: 운영 환경에서는 stub을 미리 생성

호출할 서비스의 `.proto`를 **알고 있다면**(대부분의 운영 상황), 리플렉션조차 필요 없습니다. 이 폴더의 `reflection_example.proto`처럼 **빌드 시점에 stub을 생성**해 직접 호출하는 것이 가장 안전하고 빠릅니다.

```bash
# 한 번만: proto → 파이썬 코드 생성
uv run python -m grpc_tools.protoc -I=. \
    --python_out=. --grpc_python_out=. reflection_example.proto
```

**FastAPI(async)에서 생성 stub 호출:**

```python
import grpc
import reflection_example_pb2 as pb2
import reflection_example_pb2_grpc as pb2_grpc

@app.post("/echo")
async def echo(text: str):
    async with grpc.aio.insecure_channel("localhost:50051") as channel:
        stub = pb2_grpc.EchoServiceStub(channel)
        resp = await stub.Echo(pb2.EchoRequest(message=text))
        return {"message": resp.message}
```

**Django에서 생성 stub 호출:**

```python
import grpc
import reflection_example_pb2 as pb2
import reflection_example_pb2_grpc as pb2_grpc

def echo_view(request):
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = pb2_grpc.EchoServiceStub(channel)
        resp = stub.Echo(pb2.EchoRequest(message=request.GET["text"]))
    return JsonResponse({"message": resp.message})
```

| 항목 | 동적 리플렉션(4~6장) | 미리 생성한 stub(7장) |
|---|---|---|
| proto 필요 | ❌ 런타임에 받아옴 | ✅ 빌드 시 생성 |
| 타입 안전 | 약함 | 강함 |
| 속도 | 디스크립터 조회 오버헤드 | 가장 빠름 |
| 적합 | 어드민/게이트웨이/디버그 | 일반 운영 호출 |

> ✅ 권장: **일반 호출은 7장(생성 stub)**, **"grpcurl을 웹으로"가 목적이면 4~6장(동적 리플렉션)**.

---

## 8. 안티패턴: subprocess로 grpcurl 실행 (피하세요)

참고로, "터미널 명령을 그대로 코드에 넣는" 방식은 다음과 같습니다. **권장하지 않습니다.**

```python
# ❌ 안티패턴 — 이렇게 하지 마세요
import subprocess

def list_services_bad():
    result = subprocess.run(
        ["grpcurl", "-plaintext", "localhost:50051", "list"],
        capture_output=True, text=True,
    )
    return result.stdout.splitlines()  # 텍스트 파싱에 의존 → 취약
```

문제점은 [1장](#1-왜-웹-서버에서-grpcurl을-직접-호출하면-안-되는가)과 같습니다: 프로세스 생성 비용, 텍스트 파싱 취약성, 명령어 주입 위험, 배포 시 grpcurl 바이너리 의존. **4~7장의 코드 기반 방식으로 대체하세요.**

---

## 9. 자주 발생하는 오류

| 증상 | 원인 | 해결 |
|---|---|---|
| `ModuleNotFoundError: grpc_reflection` | `grpcio-reflection` 미설치 | `uv add grpcio-reflection` 또는 `uv sync` |
| `ImportError: cannot import name 'ProtoReflectionDescriptorDatabase'` | grpcio-reflection 버전이 오래됨 | `uv add -U grpcio-reflection` (1.50+ 권장) |
| `ImportError: GetMessageClass` | protobuf 4.22 미만 | 4장 코드의 `try/except` 분기가 자동 처리(구버전은 `MessageFactory().GetPrototype`) |
| `StatusCode.UNIMPLEMENTED` | **대상 서버에 리플렉션이 꺼져 있음** | 서버에서 `reflection.enable_server_reflection(...)` 활성화 (`server.py` 참고) |
| `StatusCode.UNAVAILABLE` | 서버 미실행/주소·포트 불일치 | 서버 먼저 실행, `target` 주소 확인 |
| FastAPI 응답이 느리고 멈춤 | 동기 gRPC 호출이 이벤트 루프를 막음 | `run_in_threadpool` 사용(5장) 또는 `grpc.aio` 채널 사용 |
| `KeyError`로 서비스/메서드 못 찾음 | 전체 이름(full name) 오타 | `package.Service` 형식 확인 (예: `reflection_example.EchoService`) |

---

## 정리

- `grpcurl`은 **CLI 디버깅 도구**일 뿐, 그 기능(리플렉션 조회 + 동적 호출)은 전부 파이썬 코드로 가능합니다.
- 웹 서버 안에서는 **절대 grpcurl을 `subprocess`로 실행하지 말고**, `grpc_reflection` + `google.protobuf`로 직접 구현하세요(4~6장).
- proto를 안다면 **미리 생성한 stub**이 가장 안전하고 빠릅니다(7장).
- FastAPI는 비동기 루프를 막지 않도록 `run_in_threadpool`/`grpc.aio`를, Django는 뷰 또는 management 명령으로 감싸면 됩니다.
