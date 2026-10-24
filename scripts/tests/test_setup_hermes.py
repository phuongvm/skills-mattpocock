"""Tests for scripts/setup-hermes.py (run: uv run --with pytest --with pyyaml pytest scripts/tests)."""

import importlib.util
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "setup-hermes.py"
spec = importlib.util.spec_from_file_location("setup_hermes", SCRIPT)
setup_hermes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup_hermes)

PROFILES = ["coder", "designer", "leader", "qa", "researcher", "reviewer"]


def make_skills(root: Path, n: int) -> Path:
    skills = root / "repo" / "skills"
    for i in range(n):
        d = skills / "engineering" / f"skill-{i:02d}"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"---\nname: skill-{i:02d}\n---\n", encoding="utf-8")
    return skills


def write_cfg(path: Path, skills_dir: Path, agents: Path, *, parent_dup: bool, disabled):
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = ([str(agents)] if parent_dup else []) + [str(skills_dir)]
    data = {"model": {"default": "x"}, "skills": {"external_dirs": ext, "create_dir": str(agents / "skills")}}
    if disabled is not None:
        data["skills"]["disabled"] = list(disabled)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


@pytest.fixture
def cluster(tmp_path):
    """Hermes root + 6 profiles, all compliant."""
    skills_dir = make_skills(tmp_path, setup_hermes.EXPECTED_SKILL_COUNT)
    agents = tmp_path / ".agents"
    (agents / "skills").mkdir(parents=True)
    home = tmp_path / "hermes"
    cfgs = [home / "config.yaml"] + [home / "profiles" / p / "config.yaml" for p in PROFILES]
    for c in cfgs:
        write_cfg(c, skills_dir, agents, parent_dup=False, disabled=["keep-me", *setup_hermes.DISABLED_SKILLS])
    return {"home": home, "skills_dir": skills_dir, "agents": agents, "cfgs": cfgs}


def run(monkeypatch, home, skills_dir, *argv):
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(setup_hermes, "get_repo_skills_dir", lambda: skills_dir)
    return setup_hermes.main(list(argv))


def test_disabled_list_is_the_40_agreed_names():
    names = setup_hermes.DISABLED_SKILLS
    assert len(names) == 40 and len(set(names)) == 40
    assert {"pokemon-player", "serving-llms-vllm", "claude-handoff", "ask-matt", "loop-me"} <= set(names)
    # engineering skills we route to must never be disabled
    assert not {"diagnosing-bugs", "codebase-design", "tdd", "code-review", "grill-me", "to-tickets"} & set(names)


def test_verify_passes_on_compliant_cluster(monkeypatch, cluster):
    assert run(monkeypatch, cluster["home"], cluster["skills_dir"], "--verify") == 0


def test_verify_from_profile_home_checks_all_seven_configs(monkeypatch, cluster, capsys):
    profile_home = cluster["home"] / "profiles" / "reviewer"
    write_cfg(cluster["cfgs"][0], cluster["skills_dir"], cluster["agents"], parent_dup=True, disabled=[])
    assert run(monkeypatch, profile_home, cluster["skills_dir"], "--verify") == 1
    out = capsys.readouterr().out
    assert "Checking 7 configuration target(s)" in out


def test_verify_fails_when_parent_of_create_dir_is_external_dir(monkeypatch, cluster, capsys):
    write_cfg(cluster["cfgs"][3], cluster["skills_dir"], cluster["agents"], parent_dup=True,
              disabled=setup_hermes.DISABLED_SKILLS)
    assert run(monkeypatch, cluster["home"], cluster["skills_dir"], "--verify") == 1
    assert "double-scan" in capsys.readouterr().out


def test_verify_fails_when_a_disabled_name_is_missing(monkeypatch, cluster, capsys):
    write_cfg(cluster["cfgs"][5], cluster["skills_dir"], cluster["agents"], parent_dup=False,
              disabled=setup_hermes.DISABLED_SKILLS[1:])
    assert run(monkeypatch, cluster["home"], cluster["skills_dir"], "--verify") == 1
    assert "pokemon-player" in capsys.readouterr().out


def test_verify_fails_on_unexpected_skill_count(monkeypatch, cluster, tmp_path):
    extra = cluster["skills_dir"] / "misc" / "extra"
    extra.mkdir(parents=True)
    (extra / "SKILL.md").write_text("---\nname: extra\n---\n", encoding="utf-8")
    assert run(monkeypatch, cluster["home"], cluster["skills_dir"], "--verify") == 1


def test_verify_fails_when_skills_dir_not_registered(monkeypatch, cluster):
    data = yaml.safe_load(cluster["cfgs"][1].read_text(encoding="utf-8"))
    data["skills"]["external_dirs"] = []
    cluster["cfgs"][1].write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert run(monkeypatch, cluster["home"], cluster["skills_dir"], "--verify") == 1


def test_verify_is_read_only(monkeypatch, cluster):
    write_cfg(cluster["cfgs"][2], cluster["skills_dir"], cluster["agents"], parent_dup=True, disabled=[])
    before = [c.read_bytes() for c in cluster["cfgs"]]
    run(monkeypatch, cluster["home"], cluster["skills_dir"], "--verify")
    assert [c.read_bytes() for c in cluster["cfgs"]] == before


def test_setup_mode_repairs_configs_then_verify_passes(monkeypatch, cluster):
    for c in cluster["cfgs"]:
        write_cfg(c, cluster["skills_dir"], cluster["agents"], parent_dup=True, disabled=["keep-me"])
    assert run(monkeypatch, cluster["home"], cluster["skills_dir"]) == 0
    assert run(monkeypatch, cluster["home"], cluster["skills_dir"], "--verify") == 0
    data = yaml.safe_load(cluster["cfgs"][4].read_text(encoding="utf-8"))
    assert str(cluster["agents"]) not in data["skills"]["external_dirs"]
    assert "keep-me" in data["skills"]["disabled"]
    assert data["skills"]["create_dir"] == str(cluster["agents"] / "skills")
