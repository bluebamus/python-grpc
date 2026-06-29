"""게이트웨이 설정.

환경변수로 gRPC 백엔드 주소와 기본 데드라인을 조정할 수 있다.
실무에서는 이런 값을 코드에 하드코딩하지 않고 설정/환경변수로 분리한다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env")

    # 호출할 gRPC 서버 주소 (해당 예제의 server.py 가 띄우는 주소)
    grpc_target: str = "localhost:50056"

    # 요청에 deadline_ms 가 없을 때 적용할 기본 per-call 데드라인(ms)
    default_deadline_ms: int = 1500

    # 클라이언트 연결 끊김을 확인하는 폴링 간격(초)
    disconnect_poll_interval: float = 0.05


settings = Settings()
