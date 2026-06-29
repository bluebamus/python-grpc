"""실제 브라우저(Chromium)로 SSE / WebSocket 게이트웨이를 검증하는 E2E 테스트.

pytest-playwright 의 `page` 픽스처가 헤드리스 Chromium 을 띄운다. 브라우저의
EventSource / WebSocket 이 게이트웨이를 통해 gRPC 스트림을 소비하고, 그 결과가
DOM 에 렌더링되는지 확인한다 — httpx 기반 통합 테스트가 다루지 못하는
"진짜 브라우저 런타임" 경로를 검증한다.
"""

from playwright.sync_api import Page, expect


def test_sse_server_streaming_in_browser(live_server, page: Page):
    page.goto(f"{live_server}/")
    page.click("#start-sse")

    # 서버 스트리밍이 SSE 로 4개(hello #0..#3) 도착해 DOM 에 렌더링되어야 한다.
    expect(page.locator("#sse-status")).to_have_text("done", timeout=10_000)
    items = page.locator(".sse-item")
    expect(items).to_have_count(4)
    assert items.nth(0).inner_text() == "hello #0"
    assert items.nth(3).inner_text() == "hello #3"


def test_websocket_bidi_in_browser(live_server, page: Page):
    page.goto(f"{live_server}/")
    page.click("#start-ws")

    # 양방향: 브라우저가 a/b/c 전송 → echo: a/b/c 3개 수신해 렌더링되어야 한다.
    expect(page.locator("#ws-status")).to_have_text("done", timeout=10_000)
    items = page.locator(".ws-item")
    expect(items).to_have_count(3)
    texts = [items.nth(i).inner_text() for i in range(3)]
    assert texts == ["echo: a", "echo: b", "echo: c"]


def test_health_endpoint(live_server, page: Page):
    # 게이트웨이 자체 헬스(브라우저로 직접 접속해도 200/JSON)
    resp = page.request.get(f"{live_server}/health")
    assert resp.status == 200
    assert resp.json() == {"status": "ok"}
