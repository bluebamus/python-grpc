"""Django 게이트웨이 통합 테스트 (반이중 배치)."""

from django.test import Client

client = Client()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_batch_returns_same_count_replies(echo_server):
    messages = ["a", "b", "c"]
    resp = client.post(
        "/chat-batch",
        data={"messages": messages},
        content_type="application/json",
    )
    assert resp.status_code == 200
    replies = resp.json()["replies"]
    assert len(replies) == len(messages)
    assert replies == [f"echo: {m}" for m in messages]


def test_chat_batch_rejects_non_list():
    resp = client.post(
        "/chat-batch",
        data={"messages": "not-a-list"},
        content_type="application/json",
    )
    assert resp.status_code == 422
