"""Conversa com a API do ParaTranz."""

import time

import requests

from .config import BASE_URL, POLL_INTERVAL, POLL_MAX_TRIES, PROJECT_ID
from .errors import ApiError


def check_token(token: str) -> None:
    """Testa o token pedindo a lista de projetos."""
    try:
        r = requests.get(
            f"{BASE_URL}/projects",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
    except requests.RequestException:
        raise ApiError("Não consegui conectar ao ParaTranz. Verifique sua internet.")
    if r.status_code == 401:
        raise ApiError("Token inválido ou expirado.")
    if not r.ok:
        raise ApiError(f"O ParaTranz respondeu com erro {r.status_code}.")


def download_latest(token: str, dest: str, status, project_id: int = PROJECT_ID) -> None:
    """Dispara a exportação, espera ficar pronta e baixa o zip.
    `status(texto)` é chamado para atualizar a tela."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/projects/{project_id}/artifacts"

    def get_latest():
        r = requests.get(f"{url}/latest", headers=headers, timeout=30)
        if r.status_code == 403:
            raise ApiError("Sem permissão para ver as exportações deste projeto.")
        r.raise_for_status()
        data = r.json()
        return None if data is None else (data["id"], data["createdAt"])

    try:
        before = get_latest()

        status("Pedindo uma nova exportação...")
        r = requests.post(url, headers=headers, timeout=30)
        if r.status_code == 403:
            raise ApiError("Só administradores do projeto podem gerar exportações.")
        if r.status_code == 423:
            raise ApiError(
                "O projeto está bloqueado no momento. Tente de novo em instantes."
            )
        r.raise_for_status()

        for i in range(POLL_MAX_TRIES):
            status(
                f"Aguardando o ParaTranz preparar os arquivos... ({i * POLL_INTERVAL}s)"
            )
            time.sleep(POLL_INTERVAL)
            if get_latest() != before:
                break
        else:
            raise ApiError("Tempo esgotado esperando a exportação ficar pronta.")

        status("Baixando a tradução...")
        with requests.get(
            f"{url}/download", headers=headers, stream=True, timeout=60
        ) as resp:
            if resp.status_code == 403:
                raise ApiError("Sem permissão de download neste projeto.")
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
    except requests.RequestException as e:
        raise ApiError(f"Erro de conexão: {e}")
