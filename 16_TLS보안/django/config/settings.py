"""Django 설정 (게이트웨이 샘플).

DB 나 템플릿 등은 최소화하고, 게이트웨이 동작에 필요한 것만 둔다.
gRPC/TLS 관련 설정(주소, 루트 인증서 경로, 호스트네임 오버라이드)은
환경변수로 덮어쓸 수 있다. 인증서 경로를 코드에 하드코딩하지 않는 게 핵심.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 이 샘플(django/)의 상위 폴더(16_TLS보안/)에 기존 자체서명 인증서가 있다.
CERT_DIR = BASE_DIR.parent

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

# --- gRPC TLS 게이트웨이 설정 ---
# 호출할 gRPC 서버 주소 (TLS 보안 포트)
GRPC_TARGET = os.environ.get("GRPC_TARGET", "localhost:50066")
# 백엔드 서버 인증서를 검증할 루트 인증서(자체서명이므로 server.crt 자신).
GRPC_ROOT_CERT = os.environ.get("GRPC_ROOT_CERT", str(CERT_DIR / "server.crt"))
# 자체서명 인증서의 CN/SAN 과 접속 호스트가 다를 때만 사용(비워두면 미적용).
GRPC_SSL_TARGET_NAME_OVERRIDE = os.environ.get("GRPC_SSL_TARGET_NAME_OVERRIDE", "")
