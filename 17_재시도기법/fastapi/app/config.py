"""게이트웨이 설정.

환경변수로 gRPC 백엔드 주소와 재시도 정책을 조정할 수 있다.
실무에서는 이런 값을 코드에 하드코딩하지 않고 설정/환경변수로 분리한다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env")

    # 호출할 gRPC 서버 주소 (해당 예제의 server.py 가 띄우는 주소)
    grpc_target: str = "localhost:50051"

    # 재시도 정책 (gRPC service_config 로 채널에 주입된다)
    retry_max_attempts: int = 5
    retry_initial_backoff: str = "0.1s"
    retry_max_backoff: str = "1s"
    retry_backoff_multiplier: float = 2.0


settings = Settings()
