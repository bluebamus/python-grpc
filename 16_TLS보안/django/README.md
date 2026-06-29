# Django HTTP→gRPC 게이트웨이 (16_TLS보안)

이 예제의 gRPC 서버를 백엔드로 두고, Django 가 REST 엔드포인트를 노출하는
게이트웨이 샘플입니다. 핵심은 게이트웨이가 백엔드 gRPC 서버에
**TLS 보안 채널(`grpc.secure_channel`)** 로 연결한다는 점입니다. 평문이
아니라 서버 인증서를 검증한 뒤에만 RPC 가 흐릅니다.

## 구조

```
django/
├── manage.py
├── config/            # settings(주소/인증서 경로), urls, wsgi
├── gateway/           # app: views, urls, grpc_client(TLS 채널), proto/
├── tests/             # 통합 테스트(TLS 서버를 직접 띄움)
└── docs/index.html    # 실무 적용 가이드 문서
```

인증서는 상위 폴더(`16_TLS보안/`)의 기존 자체서명 인증서
(`server.crt`, `server.key`)를 재사용합니다. 인증서 CN/SAN 이 `localhost`
이므로 `localhost:50066` 접속 시 호스트네임 검증을 통과합니다.

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 TLS gRPC 서버 기동 (상위 폴더 예제 서버)
cd .. && uv run python server.py    # 별도 터미널 (포트 50051 기본)

# 2) 게이트웨이 기동
uv run python manage.py runserver

# 3) 호출
curl -X POST localhost:8000/hello -H "content-type: application/json" -d '{"name":"World"}'
```

> 참고: 상위 `server.py` 는 포트 50051 로 띄웁니다. 게이트웨이 기본 target 은
> 통합 테스트와 동일한 50066 이므로, 직접 연동 시
> `GRPC_TARGET=localhost:50051` 로 덮어쓰거나 서버 포트를 맞추세요.

## 테스트

```bash
uv run pytest
```

통합 테스트는 `add_secure_port` 로 TLS gRPC 서버를 50066 에 직접 띄우고,
게이트웨이가 보안 채널로 호출해 정상 응답을 받는지 검증합니다. 또한 평문
채널이 거부되는 것을 확인해 'insecure 가 아님'을 분명히 합니다.
