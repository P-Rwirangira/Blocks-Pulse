from pydantic import AnyHttpUrl

from blockpulse.chain_registry import configured_chains, enabled_chains
from blockpulse.config import Settings


def test_registry_has_three_supported_chain_definitions() -> None:
    settings = Settings(
        ethereum_rpc_urls=[AnyHttpUrl("https://eth.example")],
        base_rpc_urls=[AnyHttpUrl("https://base.example")],
        arbitrum_rpc_urls=[AnyHttpUrl("https://arb.example")],
    )

    chains = configured_chains(settings)

    assert [(chain.name, chain.chain_id) for chain in chains] == [
        ("ethereum", 1),
        ("base", 8453),
        ("arbitrum", 42161),
    ]
    assert len(enabled_chains(settings)) == 3


def test_registry_excludes_unconfigured_chains() -> None:
    settings = Settings(base_rpc_urls=[AnyHttpUrl("https://base.example")])

    assert [chain.name for chain in enabled_chains(settings)] == ["base"]

