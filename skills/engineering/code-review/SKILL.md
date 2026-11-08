---
name: code-review
description: "Review code and PRs on two axes: Standards and Spec."
---
# Code Review — two axes

Review the diff between `HEAD` and a fixed point the user supplies on two separate axes, each as a parallel sub-agent, then aggregate without merging.

## When to Use
Reviewing a branch, PR or commit range against the repo's documented coding standards (**Standards**) and against the originating issue/spec (**Spec**).

## Process
1. **Pin the fixed point**: `git rev-parse <fixed-point>` must resolve; `git diff <fixed-point>...HEAD` must be non-empty; note `git log <fixed-point>..HEAD --oneline`. Ask if no fixed point was given.
2. **Find the spec**: issue refs in commits → a path the user passed → `docs/`, `specs/`, `.scratch/` matching the branch → ask. None → Spec axis reports "no spec available".
3. **Find the standards**: every file documenting how code is written (`CODING_STANDARDS.md`, `CONTRIBUTING.md` always). Add the Fowler smell baseline as labelled judgement calls — repo standards override it; skip what tooling enforces. Smells: Mysterious Name · Duplicated Code · Feature Envy · Data Clumps · Primitive Obsession · Repeated Switches · Shotgun Surgery · Divergent Change · Speculative Generality · Message Chains · Middle Man · Refused Bequest.
4. **Spawn both sub-agents in parallel** with the diff command, commit list, their sources and briefs (under 400 words each): Standards → violations with cited rule + baseline smells with quoted hunk; Spec → missing/partial requirements, scope creep, wrong implementations, quoting the spec line.
5. **Aggregate** under `## Standards` and `## Spec`, verbatim; end with findings per axis and the worst issue within each. Never rerank across axes.

## Why two axes
Standards pass / Spec fail and Spec pass / Standards fail are both real; separate reports stop one axis masking the other.

Smell definitions with fixes and the full sub-agent briefs: `references/two-axis-review.md`.
