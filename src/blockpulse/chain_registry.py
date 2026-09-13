"""Configuration-driven registry for supported EVM chains."""

from dataclasses import dataclass

from blockpulse.config import Settings


@dataclass(frozen=True, slots=True)
class ChainDefinition:
    """Stable identity and endpoint configuration for one chain."""

    name: str
    chain_id: int
    rpc_urls: tuple[str, ...]


def configured_chains(settings: Settings) -> tuple[ChainDefinition, ...]:
    """Build the supported chain registry from typed settings."""

    return (
        ChainDefinition(
            name="ethereum",
            chain_id=1,
            rpc_urls=tuple(str(url) for url in settings.ethereum_rpc_urls),
        ),
        ChainDefinition(
            name="base",
            chain_id=settings.base_chain_id,
            rpc_urls=tuple(str(url) for url in settings.base_rpc_urls),
        ),
        ChainDefinition(
            name="arbitrum",
            chain_id=42161,
            rpc_urls=tuple(str(url) for url in settings.arbitrum_rpc_urls),
        ),
    )


def enabled_chains(settings: Settings) -> tuple[ChainDefinition, ...]:
    """Return only chains that have at least one configured endpoint."""

    return tuple(chain for chain in configured_chains(settings) if chain.rpc_urls)

