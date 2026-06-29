# Django HTTP→gRPC 게이트웨이 (8_데이터압축기법)

이 예제의 gRPC 서버를 백엔드로 두고, Django 가 REST 엔드포인트를 노출하는
게이트웨이 샘플입니다. 주제는 **데이터 압축 기법**입니다. gRPC 채널의
**기본 압축**과 **호출 단위(per-call) 압축 오버라이드**를 모두 보여주고,
압축 알고리즘(None/Deflate/Gzip)을 settings/쿼리스트링으로 선택할 수 있습니다.

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

# 1) 백엔드 gRPC 서버 기동 (상위 폴더 예제 서버, 포트 50058 로 수정 필요)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run python manage.py runserver

# 3) 호출 (압축 알고리즘 선택)
curl "localhost:8000/data/1?compression=gzip"
curl "localhost:8000/data/1?compression=none"
curl "localhost:8000/data/1?compression=deflate"
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 gRPC 서버를 직접 띄워 gzip/none/deflate 압축 호출이 모두
정상 동작하고, 알고리즘과 무관하게 복원된 데이터 크기가 동일함을 검증합니다.
이 샘플은 포트 **50058** 만 사용합니다.
