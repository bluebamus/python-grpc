"""앱 설정.

이 예제는 외부 gRPC 서버를 호출하지 않으므로(주제가 protobuf 직렬화 그 자체),
네트워크 관련 설정은 없다. 대신 API 메타데이터 정도만 설정으로 분리해 둔다.
실무에서도 이런 값을 코드 곳곳에 흩뿌리지 않고 한곳에서 관리한다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BOOKSTORE_", env_file=".env")

    app_title: str = "protobuf 직렬화 데모 (1_bookstore)"


settings = Settings()
