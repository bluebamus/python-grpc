"""게이트웨이 통합 테스트.

TestClient 로 REST 엔드포인트를 호출하고, 그 호출이 내부 gRPC 백엔드로
전달되며 압축 알고리즘 선택(채널 기본 / 호출 단위 오버라이드)이 동작하는지
end-to-end 로 확인한다.
"""

import base64

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import make_payload


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_get_data_gzip(grpc_server):
    # 호출 단위로 gzip 압축을 선택
    with TestClient(app) as client:
        resp = client.get("/data/1", params={"compression": "gzip"})
    assert resp.status_code == 200
    body = resp.json()
    expected = make_payload("1")
    assert body["data_id"] == "1"
    assert body["compression"] == "gzip"
    assert body["size"] == len(expected)
    # base64 디코딩 결과가 서버가 보낸 원본과 동일해야 한다(압축은 전송 계층).
    assert base64.b64decode(body["data_base64"]) == expected


def test_get_data_none(grpc_server):
    # 압축 없음(none)으로 호출
    with TestClient(app) as client:
        resp = client.get("/data/1", params={"compression": "none"})
    assert resp.status_code == 200
    body = resp.json()
    expected = make_payload("1")
    assert body["compression"] == "none"
    assert body["size"] == len(expected)
    assert base64.b64decode(body["data_base64"]) == expected


def test_gzip_and_none_same_size(grpc_server):
    # 압축 알고리즘이 달라도 복원된 데이터 크기는 동일해야 한다.
    with TestClient(app) as client:
        gzip_resp = client.get("/data/42", params={"compression": "gzip"})
        none_resp = client.get("/data/42", params={"compression": "none"})
    assert gzip_resp.status_code == 200
    assert none_resp.status_code == 200
    assert gzip_resp.json()["size"] == none_resp.json()["size"]
    assert gzip_resp.json()["data_base64"] == none_resp.json()["data_base64"]


def test_get_data_deflate(grpc_server):
    # (선택) deflate 케이스도 정상 동작해야 한다.
    with TestClient(app) as client:
        resp = client.get("/data/7", params={"compression": "deflate"})
    assert resp.status_code == 200
    body = resp.json()
    expected = make_payload("7")
    assert body["compression"] == "deflate"
    assert body["size"] == len(expected)
    assert base64.b64decode(body["data_base64"]) == expected


def test_get_data_default_compression(grpc_server):
    # compression 미지정 시 채널 기본 압축(config: gzip)이 적용된다.
    with TestClient(app) as client:
        resp = client.get("/data/9")
    assert resp.status_code == 200
    body = resp.json()
    assert body["compression"] == "gzip"  # 설정 기본값
    assert body["size"] == len(make_payload("9"))


def test_invalid_compression_returns_400(grpc_server):
    # 지원하지 않는 압축 알고리즘 이름 -> 400
    with TestClient(app) as client:
        resp = client.get("/data/1", params={"compression": "brotli"})
    assert resp.status_code == 400
