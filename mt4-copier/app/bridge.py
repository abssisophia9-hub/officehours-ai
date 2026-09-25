"""Files shared with the MT4 terminals through the Common Files folder."""

from __future__ import annotations

import json
import os
from pathlib import Path


def default_common_dir() -> Path:
    """Windows MT4 Common Files folder for this copier.

    Live terminals write here when the EAs use FILE_COMMON. Override with
    MT4_COPIER_DIR for tests or a non-default data folder.
    """
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "MetaQuotes" / "Terminal" / "Common" / "Files" / "MT4Copier"


def copier_dir_from_env() -> Path | None:
    raw = os.environ.get("MT4_COPIER_DIR")
    if not raw:
        return None
    return Path(raw)


def app_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_dir() -> Path:
    raw = os.environ.get("MT4_COPIER_DATA")
    if raw:
        return Path(raw)
    return app_root() / "data"


def ensure_bus(copier: Path) -> None:
    for name in ("commands", "fills", "config", "state"):
        (copier / name).mkdir(parents=True, exist_ok=True)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def atomic_write_json(path: Path, payload: object) -> None:
    text = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    atomic_write_text(path, text)


def read_json(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return None
    text = text.strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def read_jsonl(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return []
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def commands_path(copier: Path, slave_id: str) -> Path:
    return copier / "commands" / f"{slave_id}.jsonl"


def fills_path(copier: Path, slave_id: str) -> Path:
    return copier / "fills" / f"{slave_id}.jsonl"


def config_path(copier: Path, slave_id: str) -> Path:
    return copier / "config" / f"{slave_id}.json"


def snapshot_path(copier: Path) -> Path:
    return copier / "master_snapshot.json"


def status_path(copier: Path) -> Path:
    return copier / "master_status.json"


def control_path(copier: Path) -> Path:
    return copier / "control.json"
