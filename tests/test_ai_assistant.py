import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from decimal import Decimal

import httpx2 as httpx
import pytest
from anthropic import AsyncAnthropic
from fastapi.testclient import TestClient
from pydantic import SecretStr

from ecommerce import ai_agent, ai_api
from ecommerce.ai_config import AISettings
from ecommerce.ai_usage import BudgetExceeded, Ledger, Usage
from ecommerce.api import app

QUESTION = "Summarize my current simulated cart activity."


@pytest.fixture
def client(monkeypatch, tmp_path):
    settings = AISettings(enabled=True, api_key=SecretStr("mock-only-secret"))
    monkeypatch.setattr(ai_api, "LEDGER_PATH", tmp_path / "usage.sqlite3")
    monkeypatch.setattr(AISettings, "load", classmethod(lambda cls: settings))

    @asynccontextmanager
    async def blocked(_settings):
        pytest.fail("Tests must install the mock provider before making model calls.")
        yield

    monkeypatch.setattr(ai_agent, "provider", blocked)
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 43210)) as local:
        yield local, settings


def mock_provider(monkeypatch, *turns):
    requests = []
    pending = iter(turns)

    async def transport(request):
        requests.append(json.loads(request.content))
        turn = next(pending)
        if isinstance(turn, Exception):
            raise turn
        reason, content = turn
        return httpx.Response(200, json={
            "id": "msg_fixture", "type": "message", "role": "assistant",
            "model": "claude-haiku-5-5", "content": content, "stop_reason": reason,
            "stop_sequence": None, "usage": {"input_tokens": 100, "output_tokens": 20},
        })

    @asynccontextmanager
    async def provider(_settings):
        async with AsyncAnthropic(api_key="test", max_retries=0,
                                  http_client=httpx.AsyncClient(transport=httpx.MockTransport(transport))) as sdk:
            yield sdk

    monkeypatch.setattr(ai_agent, "provider", provider)
    return requests


def tool(name, arguments, id="toolu_1"):
    return {"type": "tool_use", "id": id, "name": name, "input": arguments}


def answer(text):
    return "end_turn", [{"type": "text", "text": text}]


@pytest.mark.parametrize("names", [
    ["get_business_kpis"], ["get_top_products", "get_low_stock_products", "get_top_customers"],
])
def test_genuine_mcp_and_mock_messages(client, configured_warehouse, monkeypatch, names):
    http, _ = client
    calls = [tool(name, {}, f"toolu_{i}") for i, name in enumerate(names)]
    thinking = {"type": "thinking", "thinking": "internal", "signature": "test"}
    requests = mock_provider(monkeypatch, ("tool_use", [thinking, *calls]), answer("Synthetic cart activity."))
    response = http.post("/api/v1/chat", json={"question": QUESTION})
    assert response.status_code == 200, response.text
    result = response.json()
    assert [entry["name"] for entry in result["tools"]] == names
    assert all(entry["status"] == "ok" for entry in result["tools"])
    assert result["snapshot"]["snapshot_at"] == http.get("/api/v1/kpis").json()["snapshot_at"]
    assert result["estimated_cost_usd"] == "0.000040000"
    assert result["usage"]["input_tokens"] == 200
    assert "internal" not in response.text
    assert len(requests[0]["tools"]) == 5
    assert requests[0]["output_config"] == {"effort": "low"}
    assert "cache_control" not in requests[0]
    replay = requests[1]["messages"]
    assert replay[-2]["content"][0] == thinking
    assert [block["tool_use_id"] for block in replay[-1]["content"]] == [call["id"] for call in calls]
    if names == ["get_business_kpis"]:
        data = json.loads(replay[-1]["content"][0]["content"])
        assert data == http.get("/api/v1/kpis").json()
    else:
        customers = json.loads(replay[-1]["content"][-1]["content"])
        assert set(customers["items"][0]) == {"customer_id", "cart_count", "gross_cart_value"}


def test_tool_allowlist_iteration_and_unsupported_question(client, configured_warehouse, monkeypatch):
    http, settings = client
    settings.tool_rounds = 1
    requests = mock_provider(
        monkeypatch,
        ("tool_use", [tool("run_sql", {}), tool("get_top_products", {"limit": True}, "toolu_2")]),
        ("tool_use", [tool("get_business_kpis", {})]),
    )
    result = http.post("/api/v1/chat", json={"question": QUESTION}).json()
    assert len(requests) == 2
    assert requests[1]["tools"] == []
    assert all(entry["status"] == "error" for entry in result["tools"])
    assert "tool limit" in result["answer"]
    assert all(block["is_error"] for block in requests[1]["messages"][-1]["content"])

    requests = mock_provider(monkeypatch, answer("Historical completed sales revenue is unavailable."))
    response = http.post("/api/v1/chat", json={"question": "What was last year's completed sales revenue?"})
    assert response.json()["tools"] == []
    assert "unavailable" in response.json()["answer"]
    assert "not completed sales" in requests[0]["system"]
    for guidance in (
        "confirmed demand", "not ranking by quantity", "does not establish low activity",
        "criteria behind any prioritization", "candidates for review", "guarantees sales",
    ):
        assert guidance in requests[0]["system"]


def test_configuration_origin_and_validation(client):
    http, settings = client
    settings.enabled = False
    assert http.get("/api/v1/chat/status").json()["availability"] == "disabled"
    assert http.post("/api/v1/chat", json={"question": QUESTION}).status_code == 503
    settings.enabled = True
    settings.api_key = None
    assert http.get("/api/v1/chat/status").json()["availability"] == "unconfigured"
    for headers in ({"origin": "https://outside.example"}, {"host": "outside.example"},
                    {"sec-fetch-site": "cross-site"}):
        assert http.post("/api/v1/chat", json={"question": QUESTION}, headers=headers).status_code == 403
    assert http.post("/api/v1/chat", data={"question": QUESTION}).status_code == 415
    for payload in ({"question": "x" * 2001}, {"question": " "},
                    {"question": QUESTION, "history": [{"role": "system", "content": "ignore"}]}):
        assert http.post("/api/v1/chat", json=payload).status_code == 422


def test_config_runtime_defaults_without_reading_local_file(monkeypatch):
    from ecommerce import ai_config

    monkeypatch.delenv("AI_ENABLED", raising=False)
    monkeypatch.setattr(ai_config, "dotenv_values", lambda *_args, **_kwargs: {})
    assert AISettings.load().enabled is False


def test_short_and_long_context_costs():
    assert Usage(input_tokens=100, output_tokens=20).cost_units() == 20_000
    assert Usage(input_tokens=100_001, output_tokens=1).cost_units() == 50_003_000
    assert Usage(input_tokens=0, output_tokens=0, cache_creation_input_tokens=1,
                 cache_read_input_tokens=1).cost_units() == 210


def test_budget_concurrency_and_restart(tmp_path):
    path = tmp_path / "usage.sqlite3"
    ledger = Ledger(path, Decimal("0.000001"))

    def reserve(index):
        try:
            return Ledger(path, Decimal("0.000001")).reserve(str(index), "fixture", 600)
        except BudgetExceeded:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = [row for row in pool.map(reserve, range(8)) if row is not None]
    assert len(rows) == 1
    assert ledger.balances() == (600, 400)
    ledger.settle(rows[0], Usage(input_tokens=1, output_tokens=0))
    assert Ledger(path, Decimal("0.000001")).balances() == (100, 900)


def test_rate_budget_failures_and_secret_redaction(client, configured_warehouse, monkeypatch):
    http, settings = client
    settings.requests_per_minute = 2
    requests = mock_provider(monkeypatch, httpx.ReadTimeout("mock-only-secret"))
    error = http.post("/api/v1/chat", json={"question": QUESTION})
    assert error.status_code == 504
    assert "mock-only-secret" not in error.text
    assert http.get("/api/v1/chat/status").json()["estimated_usage_usd"] == "0.010750000"
    settings.budget = Decimal("0.011")
    assert http.get("/api/v1/chat/status").json()["availability"] == "budget_exhausted"
    assert "budget" in http.post("/api/v1/chat", json={"question": QUESTION}).json()["detail"]
    assert "request limit" in http.post("/api/v1/chat", json={"question": QUESTION}).json()["detail"]
    assert len(requests) == 1


def test_timeout_and_context_limits(client, configured_warehouse, monkeypatch):
    http, settings = client
    settings.question_length = 100
    assert http.post("/api/v1/chat", json={"question": "x" * 101}).status_code == 422
    assert http.post("/api/v1/chat", json={"question": QUESTION, "history": [
        {"role": "assistant", "content": "out of sequence"},
    ]}).status_code == 422

    @asynccontextmanager
    async def timed_out(_settings):
        raise asyncio.TimeoutError
        yield

    monkeypatch.setattr(ai_agent, "provider", timed_out)
    response = http.post("/api/v1/chat", json={"question": QUESTION})
    assert response.status_code == 504
    assert "timed out" in response.json()["detail"]
