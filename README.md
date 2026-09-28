# BlockPulse

BlockPulse is a multi-chain health, liquidity, anomaly-detection, and evidence-grounded AI investigation platform.

The current repository begins with the expanded product prototype and the engineering rules that will guide the implementation. The MVP intentionally excludes profitability, trade execution, bridges, and autonomous actions.

## Phase 1 status

Phase 1 monitors Base RPC health. Phase 2 generalizes the same vertical slice across Ethereum, Base, and Arbitrum using a configuration-driven registry. Phase 3 adds configured Uniswap V2 and V3 pool monitoring with confirmed log ranges, normalized events, restartable cursors, pool metrics, and pool API routes. V3 uses official pool events plus `slot0()`/`liquidity()` state reads; it does not pretend concentrated liquidity is equivalent to V2 reserves.

```powershell
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
docker compose up -d postgres
blockpulse-collect
uvicorn blockpulse.api:app --reload
```

The collector requires a real Base RPC URL in `.env`. Tests use deterministic fakes and SQLite, so they do not require live blockchain access.

The collector can run any configured subset of the three supported chains. One chain or endpoint failing does not prevent observations from being collected for the others. Pool addresses and token metadata are supplied through `BLOCKPULSE_POOLS_JSON`. V3 pool entries should include `version: "v3"`, `fee_tier`, and `tick_spacing`.

## MVP direction

- Monitor Ethereum, Base, and Arbitrum.
- Monitor selected WETH/USDC and WBTC/USDC pools.
- Track chain health, RPC health, pool health, and asset health.
- Detect unusual behavior with robust baselines and later multivariate models.
- Explain incidents through approved read-only analytical tools and verified evidence.

## Repository guide

- `AGENTS.md` - project-wide contribution rules.
- `docs/CODING_RULES.md` - programming, data, ML, AI, testing, and security practices.
- `docs/ARCHITECTURE_RULES.md` - system boundaries and preferred patterns.
- `docs/SELF_IMPROVING.md` - process for turning failures into durable controls.
- `BlockPulse_Project_Prototype_Expanded.pdf` - full visual product and system blueprint.

## Prototype data note

Charts in the prototype are illustrative demo telemetry. They are not live measurements and must be replaced or clearly labelled when the implementation begins.
