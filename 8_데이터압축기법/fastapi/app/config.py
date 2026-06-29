"""게이트웨이 설정.

환경변수로 gRPC 백엔드 주소와 채널 기본 압축 알고리즘을 조정할 수 있다.
이 예제(8_데이터압축기법)의 주제는 "압축 기법"이다. 압축 알고리즘 선택을
코드에 하드코딩하지 않고 설정/환경변수로 분리하는 것이 실무 패턴이다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env")

    # 호출할 gRPC 서버 주소 (이 예제의 server.py 가 띄우는 주소)
    # 통합 테스트와 충돌하지 않도록 이 예제 고유 포트(50058)를 기본값으로 둔다.
    grpc_target: str = "localhost:50058"

    # 채널 단위(channel-level) 기본 압축 알고리즘.
    # none / deflate / gzip 중 하나. 호출 단위로 오버라이드하지 않으면 이 값이 쓰인다.
    default_compression: str = "gzip"


settings = Settings()
