"""Explora carpetas ``theme/theme`` y extrae información relevante de temas.

Uso:
    python inspector_temas_openxml.py

    El script solicita al usuario seleccionar una carpeta mediante un diálogo de
    Tkinter. A partir de esa ruta busca subcarpetas con la estructura
    ``theme/theme`` y, en cada una de ellas, abre el archivo ``theme1.xml``. Para
    cada archivo encontrado imprime la ruta y muestra el contenido del elemento
    ``<a:extLst>`` si existe. Además, si en la misma carpeta se encuentra un
    archivo ``themeVariantManager.xml``, imprime su contenido completo una sola
    vez al final.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Iterable
import tkinter as tk
from tkinter import filedialog
import xml.etree.ElementTree as ET

# Nombre de la etiqueta a extraer, configurable si en el futuro se desea buscar
# otra clave concreta.
TARGET_TAG = "a:extLst"
THEME_FILE_NAME = "theme1.xml"
VARIANT_MANAGER_FILE_NAMES = ["themeVariantManager.xml", "themeVarianManager.xml"]


@dataclass
class ThemeFiles:
    """Conjunto de archivos de tema detectados en una carpeta ``theme/theme``."""

    theme_path: str
    variant_manager_path: str | None


def find_theme_files(base_dir: str) -> Iterable[ThemeFiles]:
    """Encuentra rutas a ``theme1.xml`` y ``themeVariantManager.xml`` bajo carpetas ``theme/theme``.

    El archivo ``themeVariantManager.xml`` suele ubicarse en ``theme/theme/themeVariants``.
    También puede aparecer en la carpeta raíz como ``themeVariants/themeVariantManager.xml``
    (o con la variante sin la segunda "t"), por lo que se prueban ambas ubicaciones.
    Si no existe en ninguna de ellas, se omite de los resultados.
    """

    for current_root, _, files in os.walk(base_dir):
        if os.path.basename(current_root) != "theme":
            continue
        parent = os.path.basename(os.path.dirname(current_root))
        if parent != "theme":
            continue

        if THEME_FILE_NAME not in files:
            continue

        theme_path = os.path.join(current_root, THEME_FILE_NAME)
        candidate_paths = [
            os.path.join(current_root, "themeVariants", file_name)
            for file_name in VARIANT_MANAGER_FILE_NAMES
        ] + [
            os.path.join(current_root, file_name)
            for file_name in VARIANT_MANAGER_FILE_NAMES
        ] + [
            os.path.join(base_dir, "themeVariants", file_name)
            for file_name in VARIANT_MANAGER_FILE_NAMES
        ]

        variant_manager_path = next((path for path in candidate_paths if os.path.exists(path)), None)
        yield ThemeFiles(
            theme_path=theme_path,
            variant_manager_path=variant_manager_path,
        )


def get_target_elements(file_path: str) -> list[str]:
    """Carga un ``theme1.xml`` y devuelve el contenido de ``TARGET_TAG``."""

    try:
        tree = ET.parse(file_path)
    except ET.ParseError as exc:
        raise SystemExit(f"No se pudo parsear {file_path}: {exc}") from exc

    root = tree.getroot()
    matches: list[str] = []
    for element in root.iter():
        tag_without_ns = element.tag.split("}", maxsplit=1)[-1]
        if tag_without_ns == TARGET_TAG or tag_without_ns == TARGET_TAG.split(":")[-1]:
            matches.append(ET.tostring(element, encoding="unicode"))
    return matches


def read_xml_as_string(file_path: str) -> str:
    """Devuelve el XML completo del archivo indicado como cadena legible."""

    try:
        tree = ET.parse(file_path)
    except ET.ParseError as exc:
        raise SystemExit(f"No se pudo parsear {file_path}: {exc}") from exc

    return ET.tostring(tree.getroot(), encoding="unicode")


def select_base_dir() -> str | None:
    """Abre un diálogo para seleccionar la carpeta base."""

    root = tk.Tk()
    root.withdraw()
    return filedialog.askdirectory(title="Selecciona la carpeta raíz de búsqueda")


def main() -> int:
    base_dir = select_base_dir()
    if not base_dir:
        print("No se seleccionó ninguna carpeta.", file=sys.stderr)
        return 1

    if not os.path.isdir(base_dir):
        print(f"La ruta seleccionada no es una carpeta válida: {base_dir}", file=sys.stderr)
        return 1

    found = False
    variant_manager_path: str | None = None
    for theme_files in find_theme_files(base_dir):
        found = True
        print(f"Tema encontrado en: {theme_files.theme_path}")
        contents = get_target_elements(theme_files.theme_path)
        if not contents:
            print(f"  - No se encontró la etiqueta {TARGET_TAG} en el archivo.")
        else:
            for content in contents:
                print(f"  - {TARGET_TAG}: {content}")

        if variant_manager_path is None and theme_files.variant_manager_path:
            variant_manager_path = theme_files.variant_manager_path
        print()

    if not found:
        print("No se encontraron carpetas theme/theme con un theme1.xml en la ruta indicada.")
    elif variant_manager_path:
        print("Contenido de themeVariantManager.xml:")
        print(read_xml_as_string(variant_manager_path))
    else:
        print("No se encontró themeVariantManager.xml en la carpeta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
