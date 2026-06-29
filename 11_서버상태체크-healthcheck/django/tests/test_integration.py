"""Django 게이트웨이 통합 테스트."""

from django.test import Client

import health_check_pb2

client = Client()

_Status = health_check_pb2.HealthCheckResponse


def test_self_health_is_200():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_grpc_health_serving_returns_200(grpc_server_factory):
    grpc_server_factory({"api": _Status.SERVING})
    resp = client.get("/health/grpc", {"service": "api"})
    assert resp.status_code == 200
    assert resp.json() == {"service": "api", "status": "SERVING"}


def test_grpc_health_not_serving_returns_503(grpc_server_factory):
    grpc_server_factory({"api": _Status.NOT_SERVING})
    resp = client.get("/health/grpc", {"service": "api"})
    assert resp.status_code == 503
    assert resp.json() == {"service": "api", "status": "NOT_SERVING"}


def test_grpc_health_unknown_service_returns_503(grpc_server_factory):
    grpc_server_factory({"api": _Status.SERVING})
    resp = client.get("/health/grpc", {"service": "does-not-exist"})
    assert resp.status_code == 503
    assert resp.json()["status"] == "SERVICE_UNKNOWN"


def test_grpc_health_empty_service_overall(grpc_server_factory):
    grpc_server_factory({"": _Status.SERVING})
    resp = client.get("/health/grpc")
    assert resp.status_code == 200
    assert resp.json() == {"service": "", "status": "SERVING"}
