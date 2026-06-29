"""게이트웨이 설정.

환경변수로 gRPC 백엔드 주소를 조정할 수 있다.
실무에서는 이런 값을 코드에 하드코딩하지 않고 설정/환경변수로 분리한다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env")

    # 호출할 gRPC 서버 주소 (해당 예제의 server.py 가 띄우는 주소)
    # 3_ServerStreaming 예제에 배정된 포트는 50053 이다.
    grpc_target: str = "localhost:50053"

    # 서버 스트림을 받을 때 전체 스트림에 대한 데드라인(초).
    # 개별 메시지가 아니라 스트림 수신 전체에 적용된다.
    stream_timeout: float = 30.0


settings = Settings()
