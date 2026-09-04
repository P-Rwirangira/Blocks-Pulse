import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from blockpulse.rpc import JsonRpcProvider


def test_parse_block_number() -> None:
    assert JsonRpcProvider._parse_block_number({"result": "0x1234"}) == 4660


def test_rpc_observation_records_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_post(self: httpx.AsyncClient, *args: object, **kwargs: object) -> httpx.Response:
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0x10"}, request=httpx.Request("POST", "https://base.example"))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = JsonRpcProvider("base-a", 8453, "https://base.example")
    observation = asyncio.run(provider.observe_latest_block(datetime.now(UTC)))

    assert observation.success is True
    assert observation.latest_block_number == 16
    assert observation.error_type is None


def test_rpc_observation_records_http_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_post(self: httpx.AsyncClient, *args: object, **kwargs: object) -> httpx.Response:
        return httpx.Response(503, request=httpx.Request("POST", "https://base.example"))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = JsonRpcProvider("base-a", 8453, "https://base.example")
    observation = asyncio.run(provider.observe_latest_block(datetime.now(UTC)))

    assert observation.success is False
    assert observation.latest_block_number is None
    assert observation.error_type == "HTTPStatusError"
