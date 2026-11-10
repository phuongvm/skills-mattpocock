# Diagnosing Bugs

A structured engineering discipline for diagnosing bugs, test failures, flaky behavior, crashes, and performance regressions. Do not guess fixes or edit production code before establishing a reproduction feedback loop.

## When to Use

Use this skill when:
- A unit, integration, or end-to-end test fails deterministically or intermittently (flaky test).
- An application, script, or API endpoint crashes, raises an exception, returns wrong output, or times out.
- A service or query exhibits a performance regression after a change.

Do not use this skill for greenfield feature implementation where no defect or regression exists.

## Redact Secrets First

Whenever you capture or report commands, logs, stack traces, or HTTP payloads, **replace every secret, token, or credential with `<REDACTED>`**. Keep credentials in environment variables rather than command literals, and quote only the diagnostic signal lines.

---

## Phase 1: Construct a Reproduction Feedback Loop

**Never propose a code fix or hypothesis before you have a reproducible pass/fail (or threshold) loop.** Everything in later phases consumes this signal.

**Turn-1 Probe Rule:** On your **first turn**, execute the reproduction or measurement command directly from the user prompt and environment notes rather than spending turns on exploratory `ls`, `pwd`, or `find` listings:
- **Failing or flaky test (`pytest`, `unittest`):** Run `pytest <test_path>` directly.
- **Intermittent HTTP 500 endpoint (`POST /orders`):** Run `curl -i -X POST <url>` directly before reading or editing code.
- **Performance / latency regression:** Run a timing benchmark (`time curl <url>`, `hyperfine`, or `cProfile`) directly to record the **baseline** latency before touching code.
- **Rare / 1-in-N timeout (`worker.py --jobs N`):** Run a multi-iteration stress loop (`python worker.py --jobs 200` or `for i in $(seq 1 100)`) directly and report the measured **reproduction rate (`%`)**.
- **Deterministic startup crash (`KeyError`):** Run the entrypoint (`python app.py` or `pytest`) directly to capture the exact traceback before moving to later phases.

### Ways to construct the loop (in order of preference)

1. **Automated test command (`pytest`, `unittest`, `npm test`)** targeting the failing test or module.
2. **CLI or script invocation** with a fixed input that reproduces the exception or wrong output.
3. **HTTP probe (`curl`, test client)** against a local/staging server that triggers the `500` or bad payload.
4. **Captured trace replay** feeding a recorded request or event payload into the target function in isolation.
5. **Minimal harness** exercising the suspect module with mocked external dependencies.
6. **Stress / repetition loop** for intermittent or flaky defects (e.g., running the command 50–200 times to measure the failure rate: `ran 200 jobs: 4 timeouts (2.0%)`).
7. **Performance baseline timing harness** for latency/throughput regressions (`time`, `hyperfine`, `cProfile`, `pytest --durations`), recording the exact baseline vs current timing before touching code.
8. **Human-assisted UI loop (`scripts/hitl-loop.template.sh`)** — last resort **only** when an interactive GUI action cannot be driven headlessly; the script still captures structured stdout/logs for the agent.

### Phase 1 Exit Criteria

Phase 1 is complete when you have **executed at least once** a single command (unattended by default, or via `scripts/hitl-loop.template.sh` when human UI interaction is strictly unavoidable) and recorded its redacted output showing:
- **Symptom match:** It triggers the exact error, wrong output, flake rate, or timing regression reported by the user.
- **Repeatable signal:** It reliably distinguishes the broken state (red / above latency threshold) from a healthy state (green).

### When a Reproduction Loop Cannot Be Built

If you lack access to the environment, logs, or reproduction inputs (for example, the user only provides a blurry screenshot with no logs or repo access), **stop immediately**:
- Do **not** guess a fix or call `write_file` / `patch`.
- State clearly why a reproduction loop cannot be constructed and ask the user for the specific missing artifact (redacted logs, HAR trace, reproduction steps, or environment access).

---

## Phase 2: Tighten and Minimise the Scenario

Once Phase 1 has produced a working reproduction command, shrink the failing scenario before theorising:

1. **Tighten execution speed:** Narrow test selectors (`pytest tests/test_orders.py -k test_total`), skip unrelated startup steps, and pin seeds/time where possible.
2. **Minimise the input:** Reduce the input payload, row count, or configuration one factor at a time, re-running the Phase 1 command after each cut until **every remaining element is load-bearing** (e.g., `export(rows=10000)` fails with `9999` rows while `export(rows=3)` passes, isolating the boundary condition).

---

## Phase 3: Formulate Ranked Falsifiable Hypotheses

Before editing code or adding instrumentation, write down **3–5 ranked, falsifiable hypotheses** in your response or working notes:

- Use the explicit prediction format:
  > **Hypothesis N:** *If `<root cause X>` is responsible, then `<probe or input change Y>` will produce `<observable outcome Z>`.*
- Discard vague guesses that do not make a testable prediction.
- In interactive sessions where you are already pausing for user input, share the ranked list so the user can offer domain context; in unattended or autonomous execution, record the ranked hypotheses in your diagnostic output and proceed directly to Phase 4 without blocking.

---

## Phase 4: Instrument and Isolate One Variable at a Time

Test your ranked hypotheses in order (or when the user already specifies the exact symptom/module and asks only for temporary diagnostic logging, enter at Phase 4 after stating the target hypothesis), changing **one variable at a time**:

1. **Prefer direct inspection or targeted assertions** at module boundaries over broad logging.
2. **Tag every temporary debug log** written via `write_file` / `patch` with a unique searchable prefix such as `[DEBUG-a4f2]` so all temporary instrumentation can be located and removed deterministically with a single `grep` in Phase 6. Always mention in your response how to **remove / clean** the `[DEBUG-...]` logs with `grep`.
3. **For performance regressions:** Compare profiler or timing measurements against the Phase 1 **baseline** (or **bisect** across commits/tags) before attempting any optimization.

```python
# Example tagged probe during Phase 4 (to be removed in Phase 6):
logger.debug("[DEBUG-a4f2] batch_index=%d rows_written=%d", idx, count)
```

---

## Phase 5: Regression Test and Minimal Fix

Once a hypothesis is confirmed by evidence:

1. **When a clean test seam exists (standard path):**
   - Write or update the automated regression test file first (`write_file` to `tests/test_*.py`) from the Phase 2 minimal reproduction **before** modifying production code.
   - Run the test via `terminal` and confirm it fails on the bug.
   - Apply the minimal surgical fix to the production source file (`write_file` / `patch` to `<module>.py`).
   - Re-run the regression test and confirm it passes.
2. **When no clean automated test seam exists (architecture finding):**
   - Document explicitly why the current module boundary prevents an isolated unit/integration regression test.
   - Apply the minimal surgical fix to the production code.
   - Re-run the original Phase 1 reproduction command to prove the defect no longer reproduces.

---

## Phase 6: Cleanup and Verification Gate

Before declaring the bug fixed:
- [ ] Re-run the original Phase 1 reproduction command and show the green / fixed output.
- [ ] Confirm the regression test passes (or document the missing test seam from Phase 5).
- [ ] Remove all temporary `[DEBUG-...]` logs and throwaway scripts (verify with `grep`/`search_files` that zero `[DEBUG-` tags remain).
- [ ] **Mandatory Final Reply Summary:** In your final message, always include:
  1. The reproduction command output (including any measured **reproduction rate `%`**, **minimised** boundary input, or **baseline** timing measurement).
  2. A `### Ranked Hypotheses` section listing your falsifiable hypotheses (`Hypothesis 1..3`).
  3. Any `[DEBUG-...]` **cleanup / remove** (`grep`) instructions when temporary logging was added.
