"""게이트웨이 설정.

이 예제(16_TLS보안)의 핵심 설정은 TLS 관련 값이다. 백엔드 주소, 백엔드
서버 인증서를 검증할 루트 인증서 경로, 그리고 자체서명 인증서용
호스트네임 오버라이드를 모두 환경변수로 분리한다.
인증서 경로를 코드에 하드코딩하지 않는 것이 실무의 기본이다.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 이 샘플의 상위 폴더(16_TLS보안/)에 기존 자체서명 인증서가 있다.
#   app/config.py -> parents[0]=app, [1]=fastapi, [2]=16_TLS보안
_CERT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env")

    # 호출할 gRPC 서버 주소 (TLS 보안 포트)
    grpc_target: str = "localhost:50066"

    # 백엔드 서버 인증서를 검증할 루트 인증서.
    # 자체서명이므로 server.crt 자신이 곧 신뢰 앵커(root) 역할을 한다.
    grpc_root_cert: str = str(_CERT_DIR / "server.crt")

    # 자체서명 인증서의 CN/SAN 과 접속 호스트가 다를 때만 사용한다.
    # 비워두면 적용하지 않는다. (이 샘플 인증서는 CN=localhost, SAN=localhost
    # 라서 target 이 localhost 면 오버라이드 없이도 검증을 통과한다.)
    grpc_ssl_target_name_override: str = ""


settings = Settings()
