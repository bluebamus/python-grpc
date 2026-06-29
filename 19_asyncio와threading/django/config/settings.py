"""Django 설정 (작업 큐 샘플).

DB/템플릿 등은 최소화하고, 작업 큐 동작에 필요한 것만 둔다.
worker 동작 파라미터는 환경변수로 덮어쓸 수 있다.
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

# 이 샘플은 DB 를 쓰지 않지만, Django 기동을 위해 sqlite 메모리를 둔다.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

USE_TZ = True

# --- 작업 큐(worker) 설정 ---
# consumer 스레드가 작업 1건을 처리하는 데 걸리는(흉내내는) 시간(초).
WORKER_PROCESS_DELAY = float(os.environ.get("WORKER_PROCESS_DELAY", "0.01"))
