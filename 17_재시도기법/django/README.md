# Django HTTP→gRPC 게이트웨이 (17_재시도기법)

이 예제의 gRPC 서버를 백엔드로 두고, Django 가 REST 엔드포인트를 노출하는
게이트웨이 샘플입니다. gRPC 채널의 **재시도 정책**을 게이트웨이 계층에 적용해
백엔드의 일시적 실패(UNAVAILABLE)를 자동으로 흡수합니다.

## 구조

```
django/
├── manage.py
├── config/            # settings, urls, wsgi
├── gateway/           # app: views, urls, grpc_client, proto/
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 기동 (상위 폴더 예제 서버)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run python manage.py runserver

# 3) 호출
curl -X POST localhost:8000/unary -H "content-type: application/json" -d '{"message":"Hello"}'
```

## 테스트

```bash
uv run pytest
```
