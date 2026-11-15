"""Coloca a tradução no jogo e gera o zip de distribuição."""

import shutil
import zipfile
from pathlib import Path

from .config import APP_DIR, FONT_DIR_NAME, LANG_NAME, resource_path
from .errors import AppError


def find_font_dir() -> Path:
    """Procura a pasta Font ao lado do .exe (ou do main.py) e, se não achar,
    usa a que foi embutida dentro do .exe."""
    for candidate in (APP_DIR / FONT_DIR_NAME, resource_path(FONT_DIR_NAME)):
        if candidate.is_dir():
            return candidate
    raise AppError(
        f"Não encontrei a pasta '{FONT_DIR_NAME}'. Coloque-a ao lado do programa."
    )


def copy_fonts(font_dir: Path, staging: Path) -> None:
    """Copia a pasta Font para dentro de staging (a futura pt-BR)."""
    shutil.copytree(font_dir, staging / FONT_DIR_NAME, dirs_exist_ok=True)


def install_translation(staging: Path, lang_dir: Path, status) -> None:
    """Troca a pasta pt-BR do jogo pela nova (já pronta em staging)."""
    status("Instalando no Limbus Company...")
    target = lang_dir / LANG_NAME
    try:
        lang_dir.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(staging), str(target))
    except PermissionError:
        raise AppError(
            "Sem permissão para escrever na pasta do jogo. Feche o Limbus Company "
            "e tente abrir o programa como administrador."
        )
    except OSError as e:
        raise AppError(f"Erro ao instalar a tradução: {e}")


def zip_folder(src: Path, dest: Path, status) -> None:
    """Compacta TODO o conteúdo de src (caminhos relativos a src) em dest."""
    status("Compactando a tradução...")
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(src.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(src))
    except OSError as e:
        try:
            dest.unlink()
        except OSError:
            pass
        raise AppError(f"Erro ao criar o zip: {e}")
