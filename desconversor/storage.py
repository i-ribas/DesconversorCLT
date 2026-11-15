"""Token salvo e log da última execução (ficam em %APPDATA%)."""

import json
import time

from .config import CONFIG_DIR, CONFIG_FILE, LOG_FILE


def load_token() -> str | None:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8")).get("token")
    except (OSError, ValueError):
        return None


def save_token(token: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({"token": token}), encoding="utf-8")


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
