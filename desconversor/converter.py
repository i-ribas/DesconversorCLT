"""Desconversão: aplica as traduções do ParaTranz sobre os arquivos em inglês do jogo.
Nada aqui depende de interface, rede ou de pastas fixas: tudo chega por parâmetro."""

import json
import os
import re
from pathlib import Path

from .errors import AppError


# ----------------------------------------------------------------------
# LEITURA E ESCRITA
# ----------------------------------------------------------------------
def load_json(filepath: Path, warnings: list[str]):
    """Carrega um arquivo JSON (lista ou dicionário)."""
    try:
        with open(filepath, "r", encoding="utf-8-sig") as file:
            return json.load(file)
    except json.JSONDecodeError:
        warnings.append(f"Erro ao decodificar JSON em: {filepath}")
        return None


def save_json(filepath: Path, data) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8-sig") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


# ----------------------------------------------------------------------
# UM CAMPO
# ----------------------------------------------------------------------
def apply_translation_to_nested_field(
    en_entry, key: str, translation, warnings: list[str]
) -> bool:
    """Aplica uma tradução a um campo dentro de en_entry baseado em uma chave
    como 'levelList[0]-name' ou 'options[0]-result[0]'."""
    key = re.sub(r"(result|successDesc|failureDesc)\[\d+\]", r"\1", key)
    try:
        parts = key.split("-")
        current = en_entry

        for part in parts[:-1]:
            if "[" in part and "]" in part:
                list_name = part[: part.index("[")]
                index = int(part[part.index("[") + 1 : part.index("]")])
                current = current[list_name][index]
            else:
                current = current[part]

        final_field = parts[-1]
        # result/successDesc/failureDesc precisam ser listas
        if final_field in ("result", "successDesc", "failureDesc") and not isinstance(
            translation, list
        ):
            current[final_field] = [translation]
        else:
            current[final_field] = translation
        return True
    except Exception as e:
        warnings.append(f"Não foi possível aplicar a tradução para '{key}': {e}")
        return False


# ----------------------------------------------------------------------
# UM ARQUIVO
# ----------------------------------------------------------------------
def _group_by_id(translation_map: dict[str, str]) -> dict[str, list[tuple[str, str]]]:
    """Agrupa as traduções pelo que vem antes de cada "-" (o id do item).
    Dá o mesmo resultado do startswith(f"{id}-") do script original,
    só que sem comparar cada item com todas as chaves."""
    groups: dict[str, list[tuple[str, str]]] = {}
    for key, translation in translation_map.items():
        for i, ch in enumerate(key):
            if ch == "-":
                groups.setdefault(key[:i], []).append((key[i + 1 :], translation))
    return groups


def convert_file(
    en_file: Path, loc_file: Path, out_file: Path, warnings: list[str]
) -> bool:
    """Aplica as traduções de loc_file sobre o arquivo em inglês e salva em out_file."""
    en_data = load_json(en_file, warnings)
    localize_data = load_json(loc_file, warnings)
    if en_data is None or localize_data is None:
        return False

    if not isinstance(localize_data, list) or not all(
        isinstance(entry, dict) and "key" in entry and "translation" in entry
        for entry in localize_data
    ):
        warnings.append(f"Formato inesperado em: {loc_file}. Pulado.")
        return False

    # chave (id-campo) -> tradução
    translation_map = {
        entry["key"]: entry["translation"].replace("\\n", "\n")
        for entry in localize_data
        if entry["translation"].strip()
    }
    groups = _group_by_id(translation_map)

    for idx, en_entry in enumerate(en_data.get("dataList", [])):
        entry_id = str(en_entry.get("id", ""))

        if entry_id:
            for field_path, translation in groups.get(entry_id, []):
                apply_translation_to_nested_field(
                    en_entry, field_path, translation, warnings
                )
        else:
            for field_path, translation in groups.get(f"idx{idx}", []):
                try:
                    en_entry[field_path] = translation
                except Exception as e:
                    warnings.append(
                        f"Não foi possível aplicar a tradução de idx{idx}-{field_path}: {e}"
                    )

    save_json(out_file, en_data)
    return True


# ----------------------------------------------------------------------
# A PASTA INTEIRA
# ----------------------------------------------------------------------
def find_localize_root(extract_dir: Path) -> Path:
    """Acha a pasta 'Localize' dentro do zip extraído (a mais rasa, se houver
    mais de uma). Sem ela, tenta 'utf8' e por último a raiz."""
    best = None
    for root, dirs, _ in os.walk(extract_dir):
        for d in dirs:
            if d.lower() == "localize":
                p = Path(root) / d
                depth = len(p.relative_to(extract_dir).parts)
                if best is None or depth < best[0]:
                    best = (depth, p)
    if best:
        return best[1]
    utf8 = extract_dir / "utf8"
    return utf8 if utf8.is_dir() else extract_dir


def convert_translation(
    en_dir: Path, localize_root: Path, out_root: Path, status, warnings: list[str]
) -> int:
    """Percorre os EN_*.json de en_dir e gera os arquivos traduzidos em out_root.
    Retorna quantos arquivos foram convertidos."""
    jobs = []
    for root, _, files in os.walk(en_dir):
        for file in sorted(files):
            if file.endswith(".json") and file.startswith("EN_"):
                rel = os.path.relpath(root, en_dir)
                clean_name = file[3:]  # tira o "EN_"
                loc_file = localize_root / rel / clean_name
                if loc_file.exists():
                    jobs.append(
                        (Path(root) / file, loc_file, out_root / rel / clean_name)
                    )

    converted = 0
    for i, (en_file, loc_file, out_file) in enumerate(jobs, 1):
        status(f"Convertendo arquivos... ({i}/{len(jobs)})")
        try:
            if convert_file(en_file, loc_file, out_file, warnings):
                converted += 1
        except Exception as e:
            warnings.append(f"Erro ao processar {loc_file.name}: {e}")

    if converted == 0:
        found = sorted(p.name for p in localize_root.iterdir())[:8]
        raise AppError(
            "Nenhum arquivo foi convertido. A estrutura do zip do ParaTranz pode "
            f"ser diferente do esperado. Procurei em '{localize_root.name}', que "
            f"contém: {', '.join(found) or '(vazio)'}."
        )
    return converted
