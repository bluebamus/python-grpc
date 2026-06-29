"""게이트웨이 설정.

환경변수로 gRPC 백엔드 주소와 압축 방식을 조정할 수 있다.
실무에서는 이런 값을 코드에 하드코딩하지 않고 설정/환경변수로 분리한다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env")

    # 호출할 gRPC 서버 주소 (해당 예제의 server.py 가 띄우는 주소)
    # 7_데이터압축하기 예제에 배정된 고유 포트: 50057
    grpc_target: str = "localhost:50057"

    # 채널/호출에 적용할 압축 방식. 기본은 gzip.
    # gRPC 는 Gzip / Deflate / NoCompression 을 지원한다.
    grpc_compression: str = "Gzip"


settings = Settings()
