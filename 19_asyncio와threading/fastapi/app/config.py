"""앱 설정.

작업 큐의 동작(처리 지연, 큐 최대 크기)을 환경변수로 조정할 수 있다.
실무에서는 이런 값을 코드에 하드코딩하지 않고 설정/환경변수로 분리한다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKER_", env_file=".env")

    # consumer가 작업 1건을 처리하는 데 걸리는(흉내내는) 시간(초).
    # _process()가 time.sleep으로 블로킹하는 동기 작업을 모사하며,
    # asyncio 샘플은 이 블로킹을 asyncio.to_thread로 감싸 이벤트 루프를 보호한다.
    process_delay: float = 0.01

    # asyncio.Queue의 최대 크기. 0이면 무제한.
    # 양수로 두면 큐가 가득 찰 때 put이 대기(await)하여 백프레셔가 걸린다.
    queue_maxsize: int = 0


settings = Settings()
