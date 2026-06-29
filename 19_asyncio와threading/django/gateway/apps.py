from django.apps import AppConfig


class GatewayConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gateway"

    def ready(self) -> None:
        # 앱 로드 시 consumer 스레드를 1회 기동한다.
        # start_worker()는 중복 기동 방지 가드를 내장하므로,
        # ready()가 여러 번 호출되어도(예: 일부 관리 명령) 안전하다.
        from gateway import worker

        worker.start_worker()
