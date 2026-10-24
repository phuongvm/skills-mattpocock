#!/usr/bin/env python3
"""
Hermes Agent Setup & Skill Registration Script for skills-mattpocock.
Registers this repository's skills into Hermes config.yaml across root and all active profiles.

Usage:
    python scripts/setup-hermes.py           # Register and verify
    python scripts/setup-hermes.py --verify  # Run read-only verification
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


def update_config(cfg_path: Path, target_skills_dir: str, verify_only: bool = False) -> bool:
    """Ensure target_skills_dir is present in skills.external_dirs of cfg_path."""
    if not cfg_path.is_file():
        return False

    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"  [WARN] Failed to read {cfg_path}: {e}")
        return False

    skills_sec = data.setdefault("skills", {})
    ext_dirs = skills_sec.setdefault("external_dirs", [])
    if isinstance(ext_dirs, str):
        ext_dirs = [ext_dirs]

    # Normalize existing entries
    normalized = []
    for d in ext_dirs:
        try:
            normalized.append(str(Path(d).resolve()))
        except Exception:
            normalized.append(str(d))

    target_norm = str(Path(target_skills_dir).resolve())

    if target_norm in normalized:
        print(f"  [OK] {cfg_path.name}: already registered.")
        return True

    if verify_only:
        print(f"  [MISSING] {cfg_path.name}: not registered.")
        return False

    # Add and save
    ext_dirs.append(target_skills_dir)
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        print(f"  [UPDATED] {cfg_path.name}: successfully added skills dir.")
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to write {cfg_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Register skills-mattpocock into Hermes Agent config.")
    parser.add_argument("--verify", action="store_true", help="Only verify registration without modifying files")
    args = parser.parse_args()

    skills_dir = get_repo_skills_dir()
    skills = count_skills(skills_dir)
    print(f"=== Found {len(skills)} skills in {skills_dir} ===")

    hermes_home = find_hermes_home()
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
    all_ok = True
    for cfg in config_files:
        status = update_config(cfg, target_str, verify_only=args.verify)
        if not status:
            all_ok = False

    if all_ok:
        print("\nAll Hermes profiles successfully configured and aligned with skills-mattpocock.")
    else:
        print("\nSome configuration files were updated or need attention.")


if __name__ == "__main__":
    main()
