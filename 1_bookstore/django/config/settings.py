"""Django 설정 (protobuf 직렬화 데모).

이 예제는 외부 gRPC 서버를 호출하지 않는다(주제가 protobuf 직렬화 그 자체).
따라서 gRPC 관련 설정은 없다. DB 나 템플릿 등도 최소화하고, 앱 기동에 필요한
것만 둔다.
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
