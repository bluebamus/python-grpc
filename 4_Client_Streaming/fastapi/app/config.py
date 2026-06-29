"""게이트웨이 설정.

환경변수로 gRPC 백엔드 주소를 조정할 수 있다.
실무에서는 이런 값을 코드에 하드코딩하지 않고 설정/환경변수로 분리한다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env")

    # 호출할 gRPC 서버 주소 (4_Client_Streaming 예제에 배정된 포트 50054)
    grpc_target: str = "localhost:50054"


settings = Settings()
