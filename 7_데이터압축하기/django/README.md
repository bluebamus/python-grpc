# Django HTTP→gRPC 게이트웨이 (7_데이터압축하기)

이 예제의 gRPC 서버를 백엔드로 두고, Django 가 REST 엔드포인트를 노출하는
게이트웨이 샘플입니다. gRPC 채널/호출에 **gzip 압축**을 적용해, 큰 바이너리
응답(`bytes`)을 적은 네트워크 비용으로 받아 base64 로 인코딩해 응답합니다.

## 구조

```
django/
├── manage.py
├── config/            # settings, urls, wsgi
├── gateway/           # app: views, urls, grpc_client(gzip), proto/
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 기동 (상위 폴더 예제 서버, 포트 50057 로 조정 필요)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run python manage.py runserver

# 3) 호출
curl localhost:8000/data/1
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 gRPC 서버를 직접 띄워, gzip 압축 채널로 큰 반복 bytes 를 받아
정상 디코딩(size 확인)되는지와 NOT_FOUND→404 매핑을 검증합니다. **배정 포트: 50057**.
