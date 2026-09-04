"""Async JSON-RPC adapter for EVM-compatible chains."""

import time
from datetime import datetime
from typing import Any

import httpx

from blockpulse.domain import RpcObservation


class RpcProviderError(RuntimeError):
    """Raised when an RPC endpoint cannot provide a valid response."""


class JsonRpcProvider:
    """Adapter for the small JSON-RPC surface required by Phase 1."""

    def __init__(self, name: str, chain_id: int, url: str, timeout_seconds: float = 10.0) -> None:
        self.name = name
        self.chain_id = chain_id
        self.url = url
        self.timeout_seconds = timeout_seconds

    async def observe_latest_block(self, observed_at: datetime) -> RpcObservation:
        """Call eth_blockNumber and return a measured observation."""

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.url,
                    json={"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
                )
                response.raise_for_status()
                payload = response.json()
                block_number = self._parse_block_number(payload)
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            return RpcObservation(
                endpoint_name=self.name,
                chain_id=self.chain_id,
                observed_at=observed_at,
                latency_ms=latency_ms,
                success=False,
                error_type=type(exc).__name__,
            )

        return RpcObservation(
            endpoint_name=self.name,
            chain_id=self.chain_id,
            observed_at=observed_at,
            latency_ms=(time.perf_counter() - started) * 1000,
            success=True,
            latest_block_number=block_number,
        )

    @staticmethod
    def _parse_block_number(payload: dict[str, Any]) -> int:
        if "error" in payload:
            raise RpcProviderError(str(payload["error"]))
        result = payload["result"]
        if not isinstance(result, str) or not result.startswith("0x"):
            raise ValueError("RPC result is not a hexadecimal block number")
        return int(result, 16)

