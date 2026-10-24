# Hermes Agent Integration & Alignment Guide

This repository contains **Skills For Real Engineers** by Matt Pocock, adapted and integrated for **Hermes Agent** and sovereign multi-agent clusters (`agent4070`, `asus-vb`, `intel_nuc`, etc.).

---

## 1. Architecture & Mounting in Hermes

Hermes discovers skills natively via `skills.external_dirs` in `~/.hermes/config.yaml`. No symlink or manual copying is required.

To register this entire repository across Hermes profiles:
```yaml
# ~/.hermes/config.yaml (or profiles/<role>/config.yaml)
skills:
  external_dirs:
    - O:\workspaces\.agents
    - O:\workspaces\rules
    - O:\workspaces\oss\skills-mattpocock\skills
```

When configured, Hermes's `iter_skill_index_files` scans all 38 skills directly from this Git submodule. Running `git pull upstream main` updates all skills across all agents instantly.

---

## 2. Tool & Command Mapping (Claude Code $\rightarrow$ Hermes)

Matt Pocock's skills were authored with standard engineering disciplines. When executing these skills inside Hermes Agent, apply this deterministic tool translation matrix:

| Claude Code / Generic Concept | Hermes Native Tool Equivalent | Notes / Constraints |
|---|---|---|
| **Subagents / Parallel Agents** | `delegate_task(tasks=[...])` | MUST route through `custom:ai-router` (`cb-*` models). Never use original providers directly. |
| **Independent Review Subagent** | `delegate_task(profile='reviewer')` | Must use a distinct model/perspective for Standards vs Spec. |
| **Skill Invocation (`/skill-name`)** | `skill_view(name="<skill-name>")` | For disambiguated paths, use `skill_view(name="engineering/<name>")`. |
| **Terminal / Bash Tool** | `terminal(command="...")` | Runs in MSYS2/Git-Bash on Windows; use POSIX shell syntax. |
| **File Viewing** | `read_file(path="...", offset=1, limit=100)` | Bounded reads; never dump unpaginated files. |
| **File Editing** | `patch(path="...", old_string="...", new_string="...")` | Surgical find-and-replace; prefer over whole-file rewrites. |
| **File Discovery** | `search_files(pattern="...", target="...")` | Ripgrep-backed, bounded, skips system directories. |
| **Handoffs to Fresh Agents** | `delegate_task` or `kanban_create` | Multi-agent task handoffs use Kanban cards with verification evidence. |

---

## 3. Role-Based Skill Routing (Daily Disciplines)

In a multi-agent cluster, skills are not optional suggestions; they are bound to specialized roles:

### A. Coder Profile (`profiles/coder`)
- **Bug Diagnosis**: When troubleshooting any non-trivial bug, test regression, or flaky behavior, **MANDATORY**: call `skill_view(name="diagnosing-bugs")`.
  - *Hard Invariant*: Strictly follow Phase 1. You are forbidden from proposing hypotheses until a deterministic, fast (<5s) **Tight Red Loop** is verified.
- **Architecture & Interfaces**: When designing classes, modules, or services, **MANDATORY**: call `skill_view(name="codebase-design")`.
  - *Hard Invariant*: Apply the *Deletion Test*. Ensure 1 adapter = hypothetical seam; 2 adapters = real seam.
- **Implementation**: When writing new code, call `skill_view(name="tdd")`.

### B. Reviewer Profile (`profiles/reviewer`)
- **Two-Axis Review**: When reviewing PRs, branches, or Kanban handoffs, **MANDATORY**: call `skill_view(name="engineering/code-review")`.
  - *Hard Invariant*: Dispatch 2 independent parallel subagents via `delegate_task`:
    1. **Standards Axis**: Evaluates repo coding standards + the 12 Fowler Code Smells baseline.
    2. **Spec Axis**: Evaluates line-by-line fidelity against the originating issue/spec.
  - Reports are presented side-by-side without merging or cross-axis reranking.

### C. Leader / Orchestrator Profile (`profiles/leader`)
- **Requirement Clarification**: When receiving ambiguous asks or open-ended specs, **MANDATORY**: call `skill_view(name="grill-me")` or `skill_view(name="grilling")`.
  - *Hard Invariant*: Map the decision tree and ask only the *Frontier* (questions whose prerequisites are settled). Agent resolves objective facts autonomously; Commander decides trade-offs.
- **Task Decomposition**: Call `skill_view(name="to-tickets")` to decompose specs into tracer-bullet tasks with explicit blocking edges.

---

## 4. Verification & Testing

To test and verify skill availability on any node:
```bash
python scripts/setup-hermes.py --verify
```
