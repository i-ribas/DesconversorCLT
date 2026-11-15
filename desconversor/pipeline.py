"""As etapas do programa.

Cada etapa é uma função pequena que recebe o Context (o "estado" da execução),
faz o seu trabalho e guarda o resultado nele para a etapa seguinte.
'Aplicar' e 'Preparar' diferem só pela lista de etapas no final do arquivo."""

import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

from .config import EN_DIR, LANG_DIR, LANG_NAME
from .converter import convert_translation, find_localize_root
from .errors import AppError
from .installer import copy_fonts, find_font_dir, install_translation, zip_folder
from .paratranz import download_latest
from .storage import write_log


@dataclass
class Context:
    # --- entradas ---
    token: str
    status: Callable[[str], None]  # atualiza o texto de status na tela
    zip_dest: str | None = None  # onde salvar o zip (só em 'Preparar')
    en_dir: Path = EN_DIR
    lang_dir: Path = LANG_DIR
    font_dir: Path | None = None  # se None, a etapa 1 procura sozinha

    # --- preenchidos pelas etapas ---
    workdir: Path | None = None
    archive: Path | None = None
    localize_root: Path | None = None
    staging: Path | None = None
    converted: int = 0
    warnings: list[str] = field(default_factory=list)


Step = Callable[[Context], None]


# ----------------------------------------------------------------------
# ETAPAS
# ----------------------------------------------------------------------
def step_check_environment(ctx: Context) -> None:
    """Confere se o jogo e a pasta Font existem, antes de gastar tempo na rede."""
    if not ctx.en_dir.is_dir():
        raise AppError(
            f"Não encontrei os arquivos do Limbus Company em:\n{ctx.en_dir}\n"
            "O jogo está instalado nesse local?"
        )
    ctx.font_dir = ctx.font_dir or find_font_dir()


def step_download(ctx: Context) -> None:
    ctx.archive = ctx.workdir / "traducao.zip"
    download_latest(ctx.token, str(ctx.archive), ctx.status)


def step_extract(ctx: Context) -> None:
    ctx.status("Extraindo arquivos...")
    extract_dir = ctx.workdir / "extraido"
    try:
        with zipfile.ZipFile(ctx.archive) as zf:
            zf.extractall(extract_dir)
    except zipfile.BadZipFile:
        raise AppError("O arquivo baixado do ParaTranz não é um zip válido.")
    ctx.localize_root = find_localize_root(extract_dir)


def step_convert(ctx: Context) -> None:
    ctx.staging = ctx.workdir / LANG_NAME
    ctx.converted = convert_translation(
        ctx.en_dir, ctx.localize_root, ctx.staging, ctx.status, ctx.warnings
    )


def step_copy_fonts(ctx: Context) -> None:
    ctx.status("Copiando as fontes...")
    copy_fonts(ctx.font_dir, ctx.staging)


def step_install(ctx: Context) -> None:
    install_translation(ctx.staging, ctx.lang_dir, ctx.status)


def step_zip(ctx: Context) -> None:
    zip_folder(ctx.lang_dir, Path(ctx.zip_dest), ctx.status)


# ----------------------------------------------------------------------
# AS DUAS RECEITAS
# ----------------------------------------------------------------------
APPLY_STEPS: list[Step] = [
    step_check_environment,
    step_download,
    step_extract,
    step_convert,
    step_copy_fonts,
    step_install,
]

PREPARE_STEPS: list[Step] = APPLY_STEPS + [step_zip]


def run_pipeline(ctx: Context, steps: Sequence[Step]) -> Context:
    """Roda as etapas em ordem dentro de uma pasta temporária,
    que some sozinha no final (dando certo ou não)."""
    try:
        with tempfile.TemporaryDirectory(
            prefix="desconversor_", ignore_cleanup_errors=True
        ) as tmp:
            ctx.workdir = Path(tmp)
            for step in steps:
                step(ctx)
    finally:
        if ctx.warnings:
            write_log(ctx.warnings)
    return ctx
