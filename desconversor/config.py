"""Constantes e caminhos do programa.
Para ajustar projeto, cores ou pastas do jogo, mexa só aqui."""

import os
import sys
from pathlib import Path

# ----------------------------------------------------------------------
# PROGRAMA
# ----------------------------------------------------------------------
APP_TITLE = "Desconversor de Tradução"
BASE_URL = "https://paratranz.cn/api"
PROJECT_ID = 12352

IMAGE_NAME = "logo.png"
ICON_NAME = "clt_egogift.ico"
FONT_DIR_NAME = "Font"

POLL_INTERVAL = 5  # segundos entre cada checagem
POLL_MAX_TRIES = 60  # 60 x 5s = 5 minutos no máximo

# ----------------------------------------------------------------------
# CORES
# ----------------------------------------------------------------------
ACCENT = "#1F4FD8"
ACCENT_HOVER = "#173DAA"
BG_COLOR = "#14141C"
FIELD_COLOR = "#1E1E2A"
BORDER_COLOR = "#34344A"
SECONDARY_COLOR = "#2A2A3A"
MUTED_COLOR = "#A9A9BC"
ERROR_COLOR = "#FF6B6B"
SUCCESS_COLOR = "#5CE0A0"

# ----------------------------------------------------------------------
# LIMBUS COMPANY
# ----------------------------------------------------------------------
GAME_DIR = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Limbus Company")
DATA_DIR = GAME_DIR / "LimbusCompany_Data"
EN_DIR = DATA_DIR / "Assets" / "Resources_moved" / "Localize" / "en"
LANG_DIR = DATA_DIR / "Lang"
LANG_NAME = "pt-BR"

# ----------------------------------------------------------------------
# ARQUIVOS DO USUÁRIO (token e log)
# ----------------------------------------------------------------------
CONFIG_DIR = Path(os.getenv("APPDATA", Path.home())) / "DesconversorTraducao"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_FILE = CONFIG_DIR / "ultimo_log.txt"

# ----------------------------------------------------------------------
# ONDE ESTÃO OS ARQUIVOS DO PROGRAMA (logo, ícone, Font)
# ----------------------------------------------------------------------
FROZEN = getattr(sys, "frozen", False)  # True quando rodando como .exe

# Pasta com os arquivos embutidos no .exe (ou a raiz do projeto, no modo .py)
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
# Pasta onde o .exe (ou o main.py) está
APP_DIR = Path(sys.executable).parent if FROZEN else BUNDLE_DIR


def resource_path(name: str) -> Path:
    """Caminho de um arquivo embutido; funciona no .py e dentro do .exe."""
    return BUNDLE_DIR / name
