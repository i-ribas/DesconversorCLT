"""Interface gráfica (customtkinter). Aqui não há regra de negócio:
a janela só chama paratranz.check_token e pipeline.run_pipeline."""

import re
import threading
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw
from tkinter import filedialog, messagebox

from .config import (
    ACCENT,
    ACCENT_HOVER,
    APP_TITLE,
    BG_COLOR,
    BORDER_COLOR,
    CONFIG_DIR,
    ERROR_COLOR,
    FIELD_COLOR,
    GAME_FOLDER_NAME,
    ICON_NAME,
    IMAGE_NAME,
    MUTED_COLOR,
    SECONDARY_COLOR,
    SUCCESS_COLOR,
    lang_dir_for,
    resource_path,
)
from .errors import AppError
from .game import find_game_dir, validate_game_dir
from .paratranz import check_token
from .pipeline import APPLY_STEPS, PREPARE_STEPS, Context, run_pipeline
from .storage import load_token, save_game_dir, save_token


# ----------------------------------------------------------------------
# PEÇAS REUTILIZÁVEIS
# ----------------------------------------------------------------------
def load_logo(size: int = 180) -> ctk.CTkImage:
    path = resource_path(IMAGE_NAME)
    if path.exists():
        img = Image.open(path).convert("RGBA")
        img.thumbnail((size, size))
    else:
        # Imagem provisória caso você ainda não tenha colocado a sua
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((4, 4, size - 4, size - 4), fill=ACCENT)
        d.ellipse((size * 0.3, size * 0.3, size * 0.7, size * 0.7), fill="#FFFFFF")
    return ctk.CTkImage(light_image=img, dark_image=img, size=img.size)


def make_label(parent, text, size=12, bold=False, color=None, **kw):
    if color:
        kw["text_color"] = color
    font = ctk.CTkFont(size=size, weight="bold" if bold else "normal")
    return ctk.CTkLabel(parent, text=text, font=font, **kw)


def make_button(
    parent, text, command, width=320, height=50, size=16, radius=14, bold=True, **kw
):
    kw.setdefault("fg_color", ACCENT)
    kw.setdefault("hover_color", ACCENT_HOVER)
    font = ctk.CTkFont(size=size, weight="bold" if bold else "normal")
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        height=height,
        corner_radius=radius,
        font=font,
        **kw,
    )


def make_entry(parent, width, height, placeholder, **kw):
    return ctk.CTkEntry(
        parent,
        width=width,
        height=height,
        corner_radius=12,
        placeholder_text=placeholder,
        fg_color=FIELD_COLOR,
        border_color=BORDER_COLOR,
        **kw,
    )


def set_window_icon(window) -> None:
    """customtkinter coloca o ícone dele logo após abrir, então esperamos um pouco."""
    icon = resource_path(ICON_NAME)
    if icon.exists():
        window.after(250, lambda: window.iconbitmap(str(icon)))


# ----------------------------------------------------------------------
# JANELINHA: NOME DA VERSÃO
# ----------------------------------------------------------------------
class VersionDialog(ctk.CTkToplevel):
    """Pede o nome da versão e se é BETA.
    Depois de fechar, `result` é (versao, is_beta) ou None se cancelou."""

    def __init__(self, parent):
        super().__init__(parent)
        self.result = None

        self.title("Preparar Tradução")
        w, h = 380, 320
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)
        self.transient(parent)
        set_window_icon(self)

        self._build()
        self.after(200, self._activate)

    def _build(self):
        make_label(self, "Nome da versão", size=16, bold=True).pack(pady=(24, 2))
        make_label(self, 'O "v" é adicionado automaticamente', color=MUTED_COLOR).pack(
            pady=(0, 12)
        )

        self.entry = make_entry(self, 280, 40, "ex.: 1.2.0")
        self.entry.pack()
        self.entry.bind("<Return>", lambda e: self.confirm())

        self.beta_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self,
            text="É versão BETA?",
            variable=self.beta_var,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
        ).pack(pady=(16, 0))

        self.msg = make_label(self, "", color=ERROR_COLOR)
        self.msg.pack(pady=(8, 0))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=(8, 0))
        make_button(
            row,
            "Confirmar",
            self.confirm,
            width=130,
            height=38,
            size=13,
            radius=12,
            bold=False,
        ).pack(side="left", padx=6)
        make_button(
            row,
            "Cancelar",
            self.destroy,
            width=130,
            height=38,
            size=13,
            radius=12,
            bold=False,
            fg_color=SECONDARY_COLOR,
            hover_color=BORDER_COLOR,
        ).pack(side="left", padx=6)

    def _activate(self):
        try:
            self.grab_set()
            self.entry.focus()
        except Exception:
            pass  # a janela pode já ter sido fechada

    def confirm(self):
        # Remove caracteres que o Windows não aceita em nomes de arquivo
        version = re.sub(r'[\\/:*?"<>|]', "", self.entry.get()).strip()
        if not version:
            self.msg.configure(text="Digite o nome da versão.")
            return
        self.result = (version, bool(self.beta_var.get()))
        self.destroy()


# ----------------------------------------------------------------------
# JANELINHA: PASTA DO JOGO
# ----------------------------------------------------------------------
class GameDirDialog(ctk.CTkToplevel):
    """Aparece quando o jogo não está no local padrão.
    Depois de fechar, `result` é a pasta escolhida (já validada) ou None se cancelou."""

    def __init__(self, parent):
        super().__init__(parent)
        self.result = None

        self.title("Pasta do jogo")
        w, h = 420, 320
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)
        self.transient(parent)
        set_window_icon(self)

        self._build()
        self.after(200, self._activate)

    def _build(self):
        make_label(
            self,
            "Não encontrei os arquivos do Limbus Company. Clique no botão abaixo "
            f'e especifique onde a pasta do jogo "{GAME_FOLDER_NAME}" está.',
            size=14,
            wraplength=360,
            justify="center",
        ).pack(pady=(30, 22), padx=30)

        make_button(
            self,
            "Escolher pasta",
            self.choose,
            width=220,
            height=44,
            size=14,
            radius=12,
        ).pack()

        self.msg = make_label(
            self, "", color=ERROR_COLOR, wraplength=360, justify="center"
        )
        self.msg.pack(pady=(12, 0), padx=30)

        make_button(
            self,
            "Cancelar",
            self.destroy,
            width=120,
            height=34,
            size=13,
            radius=12,
            bold=False,
            fg_color=SECONDARY_COLOR,
            hover_color=BORDER_COLOR,
        ).pack(pady=(14, 0))

    def _activate(self):
        try:
            self.grab_set()
        except Exception:
            pass  # a janela pode já ter sido fechada

    def choose(self):
        path = filedialog.askdirectory(
            parent=self, title=f'Selecione a pasta "{GAME_FOLDER_NAME}"', mustexist=True
        )
        if not path:
            return  # fechou o seletor sem escolher nada

        game_dir = Path(path)
        if game_dir.name.lower() == "limbuscompany_data":
            game_dir = game_dir.parent  # escolheu a pasta de dentro, sem querer
        try:
            validate_game_dir(game_dir)
        except AppError as e:
            self.msg.configure(text=str(e))
            return

        self.result = game_dir
        self.destroy()


# ----------------------------------------------------------------------
# JANELA PRINCIPAL
# ----------------------------------------------------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry(self._centered(520, 700))
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)
        set_window_icon(self)

        self.token = load_token()
        self.game_dir: Path | None = None
        self.logo = load_logo()
        self.frame = None

        if self.token:
            self.show_main()
        else:
            self.show_setup()

    # -- helpers -------------------------------------------------------
    def _centered(self, w, h):
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 3
        return f"{w}x{h}+{x}+{y}"

    def _new_frame(self):
        if self.frame is not None:
            self.frame.destroy()
        self.frame = ctk.CTkFrame(self, fg_color="transparent")
        self.frame.pack(expand=True, fill="both", padx=40, pady=30)
        return self.frame

    @staticmethod
    def _spacer(parent):
        """Espaçador que mantém o conteúdo centralizado."""
        ctk.CTkLabel(parent, text="").pack(expand=True)

    def _fade(self, start, end, steps=12, delay=15):
        for i in range(steps + 1):
            self.attributes("-alpha", start + (end - start) * i / steps)
            self.update()
            self.after(delay)

    # -- tela 1: token -------------------------------------------------
    def show_setup(self):
        f = self._new_frame()
        self._spacer(f)

        ctk.CTkLabel(f, image=self.logo, text="").pack(pady=(0, 24))
        make_label(f, "Bem-vindo(a), Gerente", size=22, bold=True).pack(pady=(0, 8))
        make_label(
            f,
            "Coloque seu Token abaixo\n(você o encontra no seu"
            " perfil, aba de configurações).",
            size=13,
            color=MUTED_COLOR,
            wraplength=420,
            justify="center",
        ).pack(pady=(0, 18))

        self.token_entry = make_entry(f, 380, 44, "Token", show="•")
        self.token_entry.pack()
        self.token_entry.bind("<Return>", lambda e: self.confirm_token())

        self.setup_btn = make_button(
            f,
            "Confirmar",
            self.confirm_token,
            width=380,
            height=44,
            size=14,
            radius=12,
        )
        self.setup_btn.pack(pady=(12, 0))

        self.setup_msg = make_label(f, "", color=ERROR_COLOR)
        self.setup_msg.pack(pady=(10, 0))

        self._spacer(f)

    def confirm_token(self):
        token = self.token_entry.get().strip()
        if not token:
            self.setup_msg.configure(
                text="Cole o Token primeiro.", text_color=ERROR_COLOR
            )
            return
        self.setup_btn.configure(state="disabled", text="Verificando...")
        self.setup_msg.configure(text="")

        def work():
            try:
                check_token(token)
                self.after(0, lambda: self._token_ok(token))
            except AppError as e:
                msg = str(e)  # guarda o texto: 'e' some ao sair do except
                self.after(0, lambda: self._token_fail(msg))

        threading.Thread(target=work, daemon=True).start()

    def _token_fail(self, msg):
        self.setup_btn.configure(state="normal", text="Confirmar")
        self.setup_msg.configure(text=msg, text_color=ERROR_COLOR)

    def _token_ok(self, token):
        self.token = token
        save_token(token)
        self._fade(1.0, 0.0)
        self.show_main()
        self._fade(0.0, 1.0)

    # -- tela 2: principal ----------------------------------------------
    def show_main(self):
        f = self._new_frame()
        self._spacer(f)

        ctk.CTkLabel(f, image=self.logo, text="").pack(pady=(0, 20))
        make_label(f, APP_TITLE, size=24, bold=True).pack(pady=(0, 24))

        self.apply_btn = self._action_button(
            f,
            "Aplicar Tradução",
            "Coloca a tradução do ParaTranz no Limbus",
            self.on_apply,
        )
        self.prepare_btn = self._action_button(
            f,
            "Preparar Tradução",
            "Prepara um arquivo .zip para distribuição da tradução",
            self.on_prepare,
            top_pad=20,
        )

        self.progress = ctk.CTkProgressBar(
            f, width=320, mode="indeterminate", progress_color=ACCENT
        )  # só aparece durante o trabalho

        self.status = make_label(f, "", color=MUTED_COLOR, wraplength=380)
        self.status.pack(pady=(16, 0))

        self._spacer(f)

    def _action_button(self, parent, text, blurb, command, top_pad=0):
        btn = make_button(parent, text, command)
        btn.pack(pady=(top_pad, 0))
        make_label(
            parent, blurb, color=MUTED_COLOR, wraplength=320, justify="center"
        ).pack(pady=(6, 0))
        return btn

    # -- ações -----------------------------------------------------------
    def _ensure_game_dir(self) -> bool:
        """Descobre onde o jogo está. Se não achar, pergunta ao usuário
        (e lembra a resposta). Devolve False se ele cancelar."""
        game_dir = find_game_dir()
        if game_dir is None:
            dialog = GameDirDialog(self)
            self.wait_window(dialog)
            game_dir = dialog.result
            if game_dir is None:
                self.set_status("Pasta do jogo não especificada. Nada foi feito.")
                return False
            save_game_dir(game_dir)
        self.game_dir = game_dir
        return True

    def on_apply(self):
        if self._ensure_game_dir():
            self._start(APPLY_STEPS)

    def on_prepare(self):
        if not self._ensure_game_dir():
            return
        dialog = VersionDialog(self)
        self.wait_window(dialog)
        if not dialog.result:
            return
        version, is_beta = dialog.result
        filename = f"LCBR_v{version}{'-BETA' if is_beta else ''}.zip"

        dest = filedialog.asksaveasfilename(
            title="Salvar o zip da tradução",
            defaultextension=".zip",
            initialfile=filename,
            filetypes=[("Arquivo ZIP", "*.zip")],
        )
        if not dest:
            return

        # O zip não pode ser salvo dentro da própria pasta Lang
        try:
            Path(dest).resolve().relative_to(lang_dir_for(self.game_dir).resolve())
        except ValueError:
            pass  # está fora da Lang, tudo certo
        else:
            messagebox.showerror(
                APP_TITLE,
                "Não salve o zip dentro da pasta Lang do jogo.\nEscolha outro local.",
            )
            return

        self._start(PREPARE_STEPS, zip_dest=dest)

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.apply_btn.configure(state=state)
        self.prepare_btn.configure(state=state)

    def _start(self, steps, zip_dest: str | None = None):
        self._set_busy(True)
        self.progress.pack(pady=(18, 0), before=self.status)
        self.progress.start()
        self.set_status("Iniciando...")

        def post(text):
            self.after(0, lambda: self.set_status(text))

        ctx = Context(
            token=self.token, status=post, zip_dest=zip_dest, game_dir=self.game_dir
        )

        def work():
            try:
                run_pipeline(ctx, steps)
                self.after(0, lambda: self.finish(self._success_message(ctx)))
            except AppError as e:
                err = str(e)  # guarda o texto: 'e' some ao sair do except
                self.after(0, lambda: self.finish(err, error=True))
            except Exception as e:  # erro inesperado
                err = f"Erro inesperado: {e}"
                self.after(0, lambda: self.finish(err, error=True))

        threading.Thread(target=work, daemon=True).start()

    @staticmethod
    def _success_message(ctx: Context) -> str:
        msg = f"Pronto! {ctx.converted} arquivos convertidos e instalados."
        if ctx.zip_dest:
            msg += f"\nZip salvo em:\n{ctx.zip_dest}"
        if ctx.warnings:
            msg += (
                f"\n({len(ctx.warnings)} avisos, veja o ultimo_log.txt em {CONFIG_DIR})"
            )
        return msg

    def set_status(self, text):
        self.status.configure(text=text, text_color=MUTED_COLOR)

    def finish(self, text, error=False):
        self.progress.stop()
        self.progress.pack_forget()
        self._set_busy(False)
        self.status.configure(
            text=text, text_color=ERROR_COLOR if error else SUCCESS_COLOR
        )
