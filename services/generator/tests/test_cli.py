import json

from sentinel_generator.cli import main


def test_dry_run_emits_jsonl(capsys, monkeypatch) -> None:
    monkeypatch.setattr("time.sleep", lambda _: None)
    rc = main(
        [
            "--dry-run",
            "--rate",
            "100",
            "--duration",
            "0.05",
            "--seed",
            "42",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out, "expected at least one event line"
    for line in out:
        ev = json.loads(line)
        assert ev["raw"]["event_class"] in {"auth", "network", "dns"}


def test_dry_run_with_scenario_yields_attack_events(capsys, monkeypatch) -> None:
    monkeypatch.setattr("time.sleep", lambda _: None)
    rc = main(
        [
            "--dry-run",
            "--rate",
            "100",
            "--duration",
            "1",
            "--inject",
            "brute_force_ssh",
            "--seed",
            "1",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert any('"outcome": "failure"' in line and '"service": "ssh"' in line for line in out)
