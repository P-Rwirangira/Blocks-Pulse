# BlockPulse Contribution Rules

## Purpose

BlockPulse is a multi-chain health, liquidity, anomaly-detection, and evidence-grounded AI investigation platform. This repository should remain trustworthy, reproducible, and easy to explain in a technical interview.

## Before changing the repository

1. Read `docs/CODING_RULES.md` for implementation standards.
2. Read `docs/ARCHITECTURE_RULES.md` before changing boundaries between ingestion, storage, ML, or AI.
3. Read `docs/SELF_IMPROVING.md` when a failure, review comment, or design decision creates a reusable lesson.
4. Check the current Git status and preserve unrelated user changes.

## Core principles

- Measure first; detect second; explain only from verified records.
- Preserve raw observations before transformation.
- Make pipelines restartable, idempotent, observable, and testable.
- Keep deterministic rules separate from model outputs and LLM explanations.
- Do not describe illustrative telemetry as live production data.
- Prefer small, reviewable changes over broad speculative scaffolding.
- Every important chart, alert, model score, and AI answer must have a traceable source.

## Definition of done

A change is complete when the relevant tests pass, documentation is updated, failure behavior is understood, and the result can be demonstrated without relying on undocumented local state.
