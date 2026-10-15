import gzip
import importlib.machinery
import importlib.util
import tarfile
from datetime import date
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "deploy/pellow/cc-request-logs-rotate"


def _load():
    loader = importlib.machinery.SourceFileLoader("rotate_mod", str(SCRIPT))
    spec = importlib.util.spec_from_loader("rotate_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


rot = _load()
TODAY = date(2026, 10, 15)


def _mk(d: Path, *names: str, text='{"a":1}\n'):
    for n in names:
        p = d / n
        if n.endswith(".gz"):
            p.write_bytes(gzip.compress(text.encode()))
        else:
            p.write_text(text)


def test_compress_finished_days_keep_today_delete_old(tmp_path):
    _mk(tmp_path, "2026-10-15.jsonl", "2026-10-14.jsonl", "2026-10-01.jsonl",
        "2026-09-30.jsonl", "2026-09-01.jsonl.gz")
    r = rot.rotate(tmp_path, 14, TODAY)
    left = sorted(p.name for p in tmp_path.iterdir())
    # today stays plain; yesterday and 14-days-old are compressed; 15+ days deleted
    assert left == ["2026-10-01.jsonl.gz", "2026-10-14.jsonl.gz", "2026-10-15.jsonl"]
    assert r == {"compressed": 2, "deleted": 2, "archived": 0}
    assert gzip.open(tmp_path / "2026-10-14.jsonl.gz").read() == b'{"a":1}\n'


def test_boundary_exactly_14_days_is_kept_15_is_deleted(tmp_path):
    _mk(tmp_path, "2026-10-01.jsonl.gz", "2026-09-30.jsonl.gz")
    rot.rotate(tmp_path, 14, TODAY)
    assert [p.name for p in tmp_path.iterdir()] == ["2026-10-01.jsonl.gz"]


def test_idempotent_and_ignores_foreign_files(tmp_path):
    _mk(tmp_path, "2026-10-10.jsonl", "notes.txt", "2026-10-10.jsonl.bak")
    assert rot.rotate(tmp_path, 14, TODAY)["compressed"] == 1
    assert rot.rotate(tmp_path, 14, TODAY) == {"compressed": 0, "deleted": 0, "archived": 0}
    assert {p.name for p in tmp_path.iterdir()} == {"2026-10-10.jsonl.gz", "notes.txt", "2026-10-10.jsonl.bak"}


def test_archive_contains_everything_deleted_and_is_written_once(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    _mk(logs, "2026-04-17.jsonl", "2026-05-01.jsonl.gz", "2026-10-14.jsonl")
    arc = tmp_path / "old.tar.gz"
    r = rot.rotate(logs, 14, TODAY, archive=arc)
    assert r["deleted"] == 2 and r["archived"] == 2
    with tarfile.open(arc) as t:
        assert sorted(t.getnames()) == ["2026-04-17.jsonl", "2026-05-01.jsonl.gz"]
    # second run must not overwrite the one-time archive
    _mk(logs, "2026-06-01.jsonl")
    mtime = arc.stat().st_mtime_ns
    rot.rotate(logs, 14, TODAY, archive=arc)
    assert arc.stat().st_mtime_ns == mtime


def test_dry_run_changes_nothing(tmp_path):
    _mk(tmp_path, "2026-04-17.jsonl", "2026-10-13.jsonl")
    r = rot.rotate(tmp_path, 14, TODAY, archive=tmp_path / "a.tgz", dry_run=True)
    assert r["deleted"] == 1 and r["compressed"] == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == ["2026-04-17.jsonl", "2026-10-13.jsonl"]


def test_cli_silent_when_nothing_to_do(tmp_path, capsys):
    assert rot.main([str(tmp_path)]) == 0
    assert capsys.readouterr().out == ""
    assert rot.main([str(tmp_path / "missing")]) == 2
