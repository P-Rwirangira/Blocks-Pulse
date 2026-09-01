# Self-Improving Engineering Process

This document defines how BlockPulse improves through evidence rather than guesswork.

## Capture

When a defect, failed test, review comment, confusing chart, weak model result, or unsafe AI response is found, record:

- What happened
- How it was detected
- The affected layer
- The user or operational impact
- The smallest reliable reproduction

## Convert the lesson into a control

Every important lesson should become at least one of:

- A regression test
- A validation rule
- A metric or alert
- A documented architectural decision
- A clearer runbook step
- A benchmark case

Do not rely on memory or a one-time manual check.

## Review loop

At the end of each meaningful milestone:

1. Review failed tests and unresolved incidents.
2. Review data freshness, completeness, and replay results.
3. Review ML false positives and missed events.
4. Review AI numerical faithfulness, grounding, refusals, and latency.
5. Choose no more than three improvements for the next iteration.
6. Update this document or the relevant rule when the lesson is reusable.

## Improvement log format

Use entries like this in issue discussions or milestone notes:

```text
Date:
Observation:
Evidence:
Root cause:
Control added:
Follow-up:
```

## Quality gates

Before expanding scope, confirm:

- The current ingestion path can replay a known range.
- Duplicate and reorganization behavior is tested.
- Every alert can show its evidence.
- Model outputs are versioned and evaluated against a fixed fixture.
- AI answers are bounded by approved tools and validated numbers.
- New complexity solves a measured problem.
