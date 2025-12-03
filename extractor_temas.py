"""Explora carpetas ``theme/theme`` y extrae el contenido de ``<a:extLst>``.

Uso:
    python extractor_temas.py

El script solicita al usuario seleccionar una carpeta mediante un diálogo de
Tkinter. A partir de esa ruta busca subcarpetas con la estructura
``theme/theme`` y, en cada una de ellas, abre el archivo ``theme1.xml``. Para
cada archivo encontrado imprime la ruta y muestra el contenido del elemento
``<a:extLst>`` si existe.
"""
from __future__ import annotations

import os
import sys
from typing import Iterable
import tkinter as tk
from tkinter import filedialog
import xml.etree.ElementTree as ET

# Nombre de la etiqueta a extraer, configurable si en el futuro se desea buscar
# otra clave concreta.
TARGET_TAG = "a:extLst"


def find_theme_files(base_dir: str) -> Iterable[str]:
    """Encuentra rutas a ``theme1.xml`` bajo carpetas ``theme/theme``."""
    for current_root, _, files in os.walk(base_dir):
        if os.path.basename(current_root) != "theme":
            continue
        parent = os.path.basename(os.path.dirname(current_root))
        if parent != "theme":
            continue
        if "theme1.xml" in files:
            yield os.path.join(current_root, "theme1.xml")


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
    for theme_file in find_theme_files(base_dir):
        found = True
        print(f"Tema encontrado en: {theme_file}")
        contents = get_target_elements(theme_file)
        if not contents:
            print(f"  - No se encontró la etiqueta {TARGET_TAG} en el archivo.")
        else:
            for content in contents:
                print(f"  - {TARGET_TAG}: {content}")
        print()

    if not found:
        print("No se encontraron carpetas theme/theme con un theme1.xml en la ruta indicada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
