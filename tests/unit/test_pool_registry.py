from blockpulse.config import Settings
from blockpulse.pool_registry import configured_pools, pools_for_chain


def test_pool_registry_parses_configured_pool() -> None:
    settings = Settings(
        pools_json='[{"pool_id":"base-weth-usdc","chain_id":8453,"address":"0xpool",'
        '"token0_symbol":"WETH","token1_symbol":"USDC",'
        '"token0_decimals":18,"token1_decimals":6}]'
    )

    pools = configured_pools(settings)

    assert pools[0].pool_id == "base-weth-usdc"
    assert pools_for_chain(settings, 8453)[0].token1_decimals == 6


def test_empty_pool_registry_is_valid() -> None:
    assert configured_pools(Settings(pools_json="[]")) == ()

