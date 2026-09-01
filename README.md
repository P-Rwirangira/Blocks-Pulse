# BlockPulse

BlockPulse is a multi-chain health, liquidity, anomaly-detection, and evidence-grounded AI investigation platform.

The current repository begins with the expanded product prototype and the engineering rules that will guide the implementation. The MVP intentionally excludes profitability, trade execution, bridges, and autonomous actions.

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
