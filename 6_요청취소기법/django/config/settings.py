"""Django 설정 (게이트웨이 샘플).

DB 나 템플릿 등은 최소화하고, 게이트웨이 동작에 필요한 것만 둔다.
gRPC 관련 설정은 환경변수로 덮어쓸 수 있다.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-sample-key-do-not-use-in-prod")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "gateway",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# 게이트웨이 샘플은 DB 를 쓰지 않지만, Django 기동을 위해 sqlite 메모리를 둔다.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

USE_TZ = True

# --- gRPC 게이트웨이 설정 ---
GRPC_TARGET = os.environ.get("GRPC_TARGET", "localhost:50056")
# 요청에 deadline_ms 가 없을 때 적용할 기본 per-call 데드라인(ms)
GRPC_DEFAULT_DEADLINE_MS = int(os.environ.get("GRPC_DEFAULT_DEADLINE_MS", "1500"))
