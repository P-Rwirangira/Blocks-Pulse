"""Async JSON-RPC adapter for EVM-compatible chains."""

import time
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from blockpulse.domain.models import RpcObservation


class RpcProviderError(RuntimeError):
    """Raised when an RPC endpoint cannot provide a valid response."""


class RawLog(BaseModel):
    """Minimal JSON-RPC log envelope used by pool decoders."""

    address: str
    topics: list[str]
    data: str
    block_number: int = Field(ge=0)
    block_hash: str
    transaction_hash: str
    log_index: int = Field(ge=0)


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
        payload: dict[str, Any] | None = None
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.url,
                    json={"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
                )
                response.raise_for_status()
                candidate = response.json()
                if not isinstance(candidate, dict):
                    raise ValueError("RPC response is not a JSON object")
                payload = candidate
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
                raw_payload=payload,
            )

        return RpcObservation(
            endpoint_name=self.name,
            chain_id=self.chain_id,
            observed_at=observed_at,
            latency_ms=(time.perf_counter() - started) * 1000,
            success=True,
            latest_block_number=block_number,
            raw_payload=payload,
        )

    @staticmethod
    def _parse_block_number(payload: dict[str, Any]) -> int:
        if "error" in payload:
            raise RpcProviderError(str(payload["error"]))
        result = payload["result"]
        if not isinstance(result, str) or not result.startswith("0x"):
            raise ValueError("RPC result is not a hexadecimal block number")
        return int(result, 16)

    async def get_logs(
        self, address: str, from_block: int, to_block: int, topics: list[str]
    ) -> list[RawLog]:
        """Read logs for an address and inclusive block range."""

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                self.url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_getLogs",
                    "params": [
                        {
                            "address": address,
                            "fromBlock": hex(from_block),
                            "toBlock": hex(to_block),
                            "topics": [topics],
                        }
                    ],
                },
            )
            response.raise_for_status()
            payload = response.json()
            if "error" in payload:
                raise RpcProviderError(str(payload["error"]))
            return [
                RawLog(
                    address=item["address"],
                    topics=item["topics"],
                    data=item["data"],
                    block_number=int(item["blockNumber"], 16),
                    block_hash=item["blockHash"],
                    transaction_hash=item["transactionHash"],
                    log_index=int(item["logIndex"], 16),
                )
                for item in payload["result"]
            ]

    async def eth_call(self, to: str, data: str, block_tag: str = "latest") -> str:
        """Execute eth_call and return the ABI-encoded result."""

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                self.url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_call",
                    "params": [{"to": to, "data": data}, block_tag],
                },
            )
            response.raise_for_status()
            payload = response.json()
            if "error" in payload:
                raise RpcProviderError(str(payload["error"]))
            result = payload["result"]
            if not isinstance(result, str) or not result.startswith("0x"):
                raise ValueError("eth_call result is not hexadecimal")
            return result
