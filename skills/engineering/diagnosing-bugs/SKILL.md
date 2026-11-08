---
name: diagnosing-bugs
description: "Debug failing tests, bugs, errors, crashes, or regressions."
---
# Diagnosing Bugs

Structured discipline for test failures, flaky behavior, crashes and performance regressions. Never guess a fix or edit production code before a reproduction loop exists.

## When to Use
- A unit/integration/e2e test fails deterministically or intermittently.
- An app, script or endpoint crashes, raises, returns wrong output or times out.
- A service or query regressed in latency.
Not for greenfield features. Redact every secret as `<REDACTED>`.

## Phases
1. **Reproduction loop (Turn-1 probe)**: run the failing command directly (`pytest <path>`, `curl -i …`, timing harness, stress loop for 1-in-N flakes) before any `ls`/`find`. Exit when one redacted command reliably separates red from green. No environment/logs → stop and ask; never `write_file`/`patch` blind.
2. **Tighten and minimise**: narrow selectors, pin seeds/time, shrink input one factor at a time until every element is load-bearing.
3. **Ranked falsifiable hypotheses (3–5)**: "If `<cause>` then `<probe>` yields `<outcome>`"; share when pausing, else record and continue.
4. **Instrument one variable at a time**: boundary assertions first; tag temporary logs `[DEBUG-xxxx]`; compare perf to the baseline or bisect.
5. **Regression test, then minimal fix**: failing test first (`tests/test_*.py`), confirm red, surgical fix, confirm green. No seam → document, fix, re-run Phase 1.
6. **Cleanup gate**: Phase 1 green · regression test passes · zero `[DEBUG-` tags (`grep`) · final reply has repro output (rate %, minimised input or baseline), `### Ranked Hypotheses`, cleanup command.

Full phase text, loop construction order, exit criteria: `references/diagnosis-phases.md`.
