"""Django 게이트웨이 통합 테스트."""

import pytest
from django.test import Client

client = Client()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_unary_success_without_failures(grpc_server_factory):
    servicer = grpc_server_factory(fail_times=0)
    resp = client.post("/unary", data={"message": "Hello"}, content_type="application/json")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Received: Hello"
    assert servicer.calls == 1


def test_unary_retries_then_succeeds(grpc_server_factory):
    servicer = grpc_server_factory(fail_times=2)
    resp = client.post("/unary", data={"message": "Retry"}, content_type="application/json")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Received: Retry"
    assert servicer.calls == 3  # 재시도가 일어났다는 증거


def test_unary_exhausts_retries_returns_503(grpc_server_factory):
    servicer = grpc_server_factory(fail_times=100)
    resp = client.post("/unary", data={"message": "Nope"}, content_type="application/json")
    assert resp.status_code == 503
    assert servicer.calls == 5  # maxAttempts 만큼만 시도


def test_validation_rejects_empty_message():
    resp = client.post("/unary", data={"message": ""}, content_type="application/json")
    assert resp.status_code == 422
