"""Explora una carpeta en busca de temas y muestra sus claves y valores.

Uso:
    python extractor_temas.py /ruta/a/la/carpeta

El script localiza subcarpetas con la estructura ``theme/theme`` y, en cada
una de ellas, abre el archivo ``theme1.xml``. Para cada archivo encontrado se
imprime su ruta y se enumeran los elementos del XML con su llave (ruta de
etiquetas y atributo ``name`` si existe) y su contenido de texto.
"""
from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from typing import Iterable, Tuple


KeyValue = Tuple[str, str]


def build_key_paths(element: ET.Element, prefix: str | None = None) -> Iterable[KeyValue]:
    """Itera sobre los elementos descendientes devolviendo la llave y el texto.

    La "llave" incluye el nombre de la etiqueta y, si el elemento tiene el
    atributo ``name``, se agrega para facilitar la identificación. Cada nivel
    se separa con ``/`` para reflejar la jerarquía.
    """

    label = element.tag
    name_attr = element.get("name")
    if name_attr:
        label = f"{label}[name={name_attr}]"

    current_path = f"{prefix}/{label}" if prefix else label
    text = (element.text or "").strip()
    if text:
        yield current_path, text

    for child in element:
        yield from build_key_paths(child, current_path)


def parse_theme_file(file_path: str) -> list[KeyValue]:
    """Carga un ``theme1.xml`` y devuelve las llaves con su contenido."""
    try:
        tree = ET.parse(file_path)
    except ET.ParseError as exc:
        raise SystemExit(f"No se pudo parsear {file_path}: {exc}") from exc

    root = tree.getroot()
    return list(build_key_paths(root))


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Busca carpetas theme/theme dentro de una ruta dada y muestra el contenido "
            "de cada theme1.xml"
        )
    )
    parser.add_argument(
        "ruta",
        help="Carpeta raíz donde buscar temas",
    )
    args = parser.parse_args()

    base_dir = args.ruta
    if not os.path.isdir(base_dir):
        print(f"La ruta proporcionada no es una carpeta válida: {base_dir}", file=sys.stderr)
        return 1

    found = False
    for theme_file in find_theme_files(base_dir):
        found = True
        print(f"Tema encontrado en: {theme_file}")
        for key, value in parse_theme_file(theme_file):
            print(f"  - {key}: {value}")
        print()

    if not found:
        print("No se encontraron carpetas theme/theme con un theme1.xml en la ruta indicada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
