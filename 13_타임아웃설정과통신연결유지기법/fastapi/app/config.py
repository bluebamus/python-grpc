"""게이트웨이 설정.

이 예제(13_타임아웃설정과통신연결유지기법)의 주제는 두 가지다.

1. **per-call deadline(timeout)**: 개별 RPC 호출에 데드라인을 걸어, 백엔드가
   너무 오래 걸리면 호출을 끊고 `DEADLINE_EXCEEDED` 로 만든다.
2. **keepalive**: 유휴 연결이라도 주기적으로 HTTP/2 PING 을 보내 연결이
   살아있는지 확인하고, 죽은 연결을 빨리 감지한다.

실무에서는 이런 값을 코드에 하드코딩하지 않고 설정/환경변수로 분리한다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env")

    # 호출할 gRPC 서버 주소 (해당 예제의 server.py 가 띄우는 주소)
    grpc_target: str = "localhost:50063"

    # --- per-call deadline(timeout) ---
    # REST 요청이 deadline_ms 를 주지 않으면 이 기본값(ms)을 데드라인으로 쓴다.
    default_deadline_ms: int = 1000

    # --- keepalive 옵션 (채널에 주입) ---
    # 이 시간(ms)마다 유휴 연결에 PING 을 보내 살아있는지 확인한다.
    keepalive_time_ms: int = 10000
    # PING 응답을 이 시간(ms) 안에 못 받으면 연결이 죽은 것으로 본다.
    keepalive_timeout_ms: int = 5000
    # 진행 중인 호출이 없어도 PING 을 보낼지 여부 (1=허용).
    keepalive_permit_without_calls: int = 1
    # 데이터 프레임 없이 보낼 수 있는 최대 PING 횟수 (0=무제한).
    http2_max_pings_without_data: int = 0


settings = Settings()
