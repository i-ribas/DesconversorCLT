"""Configurações salvas (token e pasta do jogo) e log da última execução.
Tudo fica em %APPDATA%\\DesconversorTraducao."""

import json
import time
from pathlib import Path

from .config import CONFIG_DIR, CONFIG_FILE, LOG_FILE


def _read() -> dict:
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _update(**values) -> None:
    """Grava os valores sem apagar os que já estavam salvos."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = _read()
    data.update(values)
    CONFIG_FILE.write_text(json.dumps(data), encoding="utf-8")


def load_token() -> str | None:
    return _read().get("token")


def save_token(token: str) -> None:
    _update(token=token)


def load_game_dir() -> Path | None:
    value = _read().get("game_dir")
    return Path(value) if value else None


def save_game_dir(game_dir: Path) -> None:
    _update(game_dir=str(game_dir))


def write_log(warnings: list[str]) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        lines = [f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {len(warnings)} aviso(s)"]
        lines += warnings[:500]
        if len(warnings) > 500:
            lines.append(f"... e mais {len(warnings) - 500} aviso(s)")
        LOG_FILE.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        pass
