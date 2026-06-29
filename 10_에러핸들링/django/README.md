# Django HTTP→gRPC 게이트웨이 (10_에러핸들링)

이 예제의 gRPC 서버를 백엔드로 두고, Django 가 REST 엔드포인트를 노출하는
게이트웨이 샘플입니다. 핵심은 **gRPC 에러를 HTTP 의미로 번역**하는 것입니다.
`Calculator.Divide` 는 `divisor=0` 일 때 `INVALID_ARGUMENT` 로 abort 하고,
게이트웨이는 이를 **HTTP 400** 으로 매핑하며 에러 상세(details)도 응답에 담습니다.

## 구조

```
django/
├── manage.py
├── config/            # settings, urls, wsgi
├── gateway/           # app: views(매핑 표), urls, grpc_client, proto/
├── tests/             # 통합 테스트
└── docs/index.html    # 실무 적용 가이드 문서
```

## 설치 & 실행

```bash
uv sync

# 1) 백엔드 gRPC 서버 기동 (상위 폴더 예제 서버, 포트 50060)
cd .. && uv run python server.py    # 별도 터미널

# 2) 게이트웨이 기동
uv run python manage.py runserver

# 3) 호출
curl -X POST localhost:8000/divide -H "content-type: application/json" -d '{"dividend":10,"divisor":2}'
# -> {"quotient":5.0,"elapsed_ms":...}

curl -X POST localhost:8000/divide -H "content-type: application/json" -d '{"dividend":10,"divisor":0}'
# -> HTTP 400 {"error":{"grpc_status":"INVALID_ARGUMENT",...}}
```

## 테스트

```bash
uv run pytest
```

통합 테스트는 결정론적 gRPC 서버를 직접 띄워 에러 매핑(200 / 400 / 403)을
end-to-end 로 검증합니다. 자세한 설명은 `docs/index.html` 참고.
