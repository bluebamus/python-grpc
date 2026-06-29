"""게이트웨이 설정.

환경변수로 gRPC 헬스체크 서버 주소를 조정할 수 있다.
실무에서는 이런 값을 코드에 하드코딩하지 않고 설정/환경변수로 분리한다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env")

    # 호출할 gRPC 헬스체크 서버 주소 (이 예제의 server.py 가 띄우는 주소)
    grpc_target: str = "localhost:50061"

    # Check 호출 데드라인(초). 헬스체크는 빨라야 하므로 짧게 둔다.
    health_timeout: float = 2.0


settings = Settings()
