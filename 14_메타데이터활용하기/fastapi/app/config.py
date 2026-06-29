"""게이트웨이 설정.

환경변수로 gRPC 백엔드 주소를 조정할 수 있다.
실무에서는 이런 값을 코드에 하드코딩하지 않고 설정/환경변수로 분리한다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env")

    # 호출할 gRPC 서버 주소.
    # 이 예제(14_메타데이터활용하기)의 배정 포트는 50064 이다.
    grpc_target: str = "localhost:50064"

    # gRPC 호출 데드라인(초). 메타데이터 왕복은 가벼우므로 짧게 둔다.
    grpc_timeout: float = 5.0


settings = Settings()
