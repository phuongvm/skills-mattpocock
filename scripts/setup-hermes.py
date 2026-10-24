#!/usr/bin/env python3
"""
Hermes Agent Setup & Skill Registration Script for skills-mattpocock.
Registers this repository's skills into Hermes config.yaml across root and all active profiles,
and enforces skill hygiene: no external_dirs entry that double-scans skills.create_dir, and the
agreed DISABLED_SKILLS present in skills.disabled.

Usage:
    python scripts/setup-hermes.py           # Register, repair hygiene, then verify
    python scripts/setup-hermes.py --verify  # Read-only verification (exit 1 on any drift)
"""

import os
import sys
import argparse
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Run 'pip install pyyaml' or activate Hermes PM environment.")
    sys.exit(1)


# Number of SKILL.md files this repository ships; --verify fails if the tree drifts.
EXPECTED_SKILL_COUNT = 38

# Skills irrelevant to this cluster's engineering work (non-engineering bundled defaults) or
# Claude-Code/author-specific Matt Pocock skills. Kept in skills.disabled of every config.
DISABLED_SKILLS = [
    # Non-engineering / niche bundled defaults
    "pokemon-player", "minecraft-modpack-server", "heartmula", "spotify", "gif-search",
    "touchdesigner-mcp", "axolotl", "unsloth", "obliteratus", "clip", "segment-anything-model",
    "stable-diffusion-image-generation", "whisper", "llama-cpp", "serving-llms-vllm", "outlines",
    "paddle-sandbox-testing", "stripe-link-cli", "stripe-projects", "mpp-agent",
    "hpx-high-performance-framework", "business-plan-financial-modeling", "reddit-reading", "xitter",
    "blogwatcher", "baoyu-infographic", "comfyui", "research-paper-writing", "rss-feeds",
    # Claude-Code / author-specific Matt Pocock skills
    "claude-handoff", "git-guardrails-claude-code", "setup-matt-pocock-skills", "migrate-to-shoehorn",
    "scaffold-exercises", "setup-pre-commit", "writing-beats", "writing-fragments", "writing-shape",
    "ask-matt", "loop-me",
]


def find_hermes_home() -> Path:
    """Find Hermes home directory using environment variables or standard paths."""
    if "HERMES_HOME" in os.environ and os.environ["HERMES_HOME"].strip():
        p = Path(os.environ["HERMES_HOME"]).resolve()
        if p.is_dir():
            return p

    # Standard cluster conventions
    candidates = [
        Path("O:/workspaces/_config/agent4070/hermes"),
        Path("O:/workspaces/_config/asus-vb/hermes"),
        Path.home() / ".hermes",
        Path.home() / "_config" / "hermes",
    ]
    for c in candidates:
        if c.is_dir() and (c / "config.yaml").is_file():
            return c.resolve()

    # Fallback to ~/.hermes
    fallback = (Path.home() / ".hermes").resolve()
    return fallback


def find_root_home(hermes_home: Path) -> Path:
    """A profile home (<root>/profiles/<name>) maps back to the root so every profile is checked."""
    if hermes_home.parent.name == "profiles" and (hermes_home.parent.parent / "config.yaml").is_file():
        return hermes_home.parent.parent
    return hermes_home


def get_repo_skills_dir() -> Path:
    """Return absolute path to the skills directory in this repository."""
    repo_root = Path(__file__).resolve().parent.parent
    skills_dir = repo_root / "skills"
    if not skills_dir.is_dir():
        raise FileNotFoundError(f"Skills directory not found at {skills_dir}")
    return skills_dir


def count_skills(skills_dir: Path) -> list[tuple[str, Path]]:
    """Scan and list all valid SKILL.md files."""
    skills = []
    for p in sorted(skills_dir.rglob("SKILL.md")):
        # Skip node_modules or backup folders
        if "node_modules" in p.parts or ".git" in p.parts:
            continue
        rel = p.relative_to(skills_dir)
        skill_name = p.parent.name
        skills.append((skill_name, rel))
    return skills


def _norm(d) -> Path:
    try:
        return Path(str(d)).resolve()
    except Exception:
        return Path(str(d))


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def double_scan_dirs(skills_sec: dict) -> list:
    """external_dirs entries equal to, or an ancestor of, skills.create_dir (scanned twice)."""
    create_dir = skills_sec.get("create_dir")
    if not create_dir:
        return []
    cd = _norm(create_dir)
    return [d for d in _as_list(skills_sec.get("external_dirs")) if _norm(d) == cd or _norm(d) in cd.parents]


def check_config(data: dict, target_skills_dir: str) -> list[str]:
    """Return human-readable problems for one parsed config (empty list = compliant)."""
    problems = []
    skills_sec = data.get("skills") or {}
    ext_dirs = _as_list(skills_sec.get("external_dirs"))
    if _norm(target_skills_dir) not in [_norm(d) for d in ext_dirs]:
        problems.append(f"skills dir not registered in external_dirs: {target_skills_dir}")
    for d in double_scan_dirs(skills_sec):
        problems.append(f"external_dirs entry {d} would double-scan create_dir {skills_sec.get('create_dir')}")
    disabled = set(_as_list(skills_sec.get("disabled")))
    missing = [n for n in DISABLED_SKILLS if n not in disabled]
    if missing:
        problems.append(f"{len(missing)} skill(s) missing from skills.disabled: {', '.join(missing)}")
    return problems


def repair_config(data: dict, target_skills_dir: str) -> None:
    """Apply registration + hygiene fixes in place (create_dir and other entries untouched)."""
    skills_sec = data.setdefault("skills", {})
    bad = {str(d) for d in double_scan_dirs(skills_sec)}
    ext_dirs = [d for d in _as_list(skills_sec.get("external_dirs")) if str(d) not in bad]
    if _norm(target_skills_dir) not in [_norm(d) for d in ext_dirs]:
        ext_dirs.append(target_skills_dir)
    skills_sec["external_dirs"] = ext_dirs
    disabled = _as_list(skills_sec.get("disabled"))
    disabled += [n for n in DISABLED_SKILLS if n not in disabled]
    skills_sec["disabled"] = disabled


def process_config(cfg_path: Path, target_skills_dir: str, verify_only: bool = False) -> bool:
    """Verify (and unless verify_only, repair) one config. True when compliant afterwards."""
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"  [WARN] Failed to read {cfg_path}: {e}")
        return False

    problems = check_config(data, target_skills_dir)
    if not problems:
        print(f"  [OK] {cfg_path}: registered, no double-scan, {len(DISABLED_SKILLS)} hygiene skills disabled.")
        return True

    if verify_only:
        for p in problems:
            print(f"  [DRIFT] {cfg_path}: {p}")
        return False

    repair_config(data, target_skills_dir)
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    except Exception as e:
        print(f"  [ERROR] Failed to write {cfg_path}: {e}")
        return False
    print(f"  [UPDATED] {cfg_path}: fixed {len(problems)} issue(s).")
    return not check_config(data, target_skills_dir)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Register skills-mattpocock into Hermes Agent config.")
    parser.add_argument("--verify", action="store_true", help="Only verify registration without modifying files")
    args = parser.parse_args(argv)

    skills_dir = get_repo_skills_dir()
    skills = count_skills(skills_dir)
    print(f"=== Found {len(skills)} skills in {skills_dir} (expected {EXPECTED_SKILL_COUNT}) ===")
    all_ok = len(skills) == EXPECTED_SKILL_COUNT
    if not all_ok:
        print(f"  [DRIFT] skill count {len(skills)} != {EXPECTED_SKILL_COUNT}")

    hermes_home = find_root_home(find_hermes_home())
    print(f"=== Hermes Home detected: {hermes_home} ===")

    config_files = [hermes_home / "config.yaml"]
    profiles_dir = hermes_home / "profiles"
    if profiles_dir.is_dir():
        for p in sorted(profiles_dir.iterdir()):
            cfg = p / "config.yaml"
            if cfg.is_file():
                config_files.append(cfg)

    print(f"Checking {len(config_files)} configuration target(s)...")
    target_str = str(skills_dir)
    for cfg in config_files:
        if not cfg.is_file() or not process_config(cfg, target_str, verify_only=args.verify):
            all_ok = False

    if all_ok:
        print("\nAll Hermes profiles successfully configured and aligned with skills-mattpocock.")
        return 0
    print("\nSome configuration files drifted or need attention.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
