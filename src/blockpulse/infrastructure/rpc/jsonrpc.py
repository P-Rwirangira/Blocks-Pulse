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
        """Read the latest block number and hashes for continuity checks."""

        started = time.perf_counter()
        payload: dict[str, Any] | None = None
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_getBlockByNumber",
                        "params": ["latest", False],
                    },
                )
                response.raise_for_status()
                candidate = response.json()
                if not isinstance(candidate, dict):
                    raise ValueError("RPC response is not a JSON object")
                payload = candidate
                block_number, block_hash, parent_hash = self._parse_block_reference(payload)
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
            latest_block_hash=block_hash,
            latest_parent_hash=parent_hash,
            raw_payload=payload,
        )

    async def get_block_by_number(self, block_tag: str) -> dict[str, Any]:
        """Read one block header and transaction-hash list for historical sampling."""

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                self.url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_getBlockByNumber",
                    "params": [block_tag, False],
                },
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or "result" not in payload:
                raise RpcProviderError("RPC block response is not an object")
            if "error" in payload:
                raise RpcProviderError(str(payload["error"]))
            result = payload["result"]
            if not isinstance(result, dict):
                raise RpcProviderError("historical block was not found")
            return result

    @staticmethod
    def _parse_block_reference(payload: dict[str, Any]) -> tuple[int, str | None, str | None]:
        """Parse a block object or a legacy hexadecimal block response."""

        if "error" in payload:
            raise RpcProviderError(str(payload["error"]))
        result = payload["result"]
        if isinstance(result, str):
            return int(result, 16), None, None
        if not isinstance(result, dict):
            raise ValueError("RPC block result is not an object")
        number = result["number"]
        block_hash = result.get("hash")
        parent_hash = result.get("parentHash")
        if not isinstance(number, str) or not number.startswith("0x"):
            raise ValueError("RPC block number is not hexadecimal")
        if block_hash is not None and not isinstance(block_hash, str):
            raise ValueError("RPC block hash is not a string")
        if parent_hash is not None and not isinstance(parent_hash, str):
            raise ValueError("RPC parent hash is not a string")
        return int(number, 16), block_hash, parent_hash

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
