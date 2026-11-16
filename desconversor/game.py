"""Onde o Limbus Company está instalado."""

from pathlib import Path

from .config import (
    DEFAULT_GAME_DIR,
    GAME_FOLDER_NAME,
    data_dir_for,
    en_dir_for,
)
from .errors import AppError
from .storage import load_game_dir


def validate_game_dir(game_dir: Path) -> None:
    """Levanta AppError (com mensagem amigável) se a pasta não serve."""
    if not data_dir_for(game_dir).is_dir():
        raise AppError(
            "Essa pasta não parece ser a do jogo. Procure a pasta chamada "
            f'"{GAME_FOLDER_NAME}" (ela contém a pasta LimbusCompany_Data).'
        )
    en_dir = en_dir_for(game_dir)
    if not en_dir.is_dir():
        raise AppError(
            "Encontrei o jogo, mas não a pasta com os arquivos em inglês "
            f"({en_dir.relative_to(game_dir)})."
        )


def is_valid_game_dir(game_dir: Path) -> bool:
    try:
        validate_game_dir(game_dir)
        return True
    except AppError:
        return False


def find_game_dir() -> Path | None:
    """A pasta que o usuário já escolheu antes (se ainda valer) ou a padrão
    da Steam. Devolve None se nenhuma das duas servir."""
    for candidate in (load_game_dir(), DEFAULT_GAME_DIR):
        if candidate is not None and is_valid_game_dir(candidate):
            return candidate
    return None
