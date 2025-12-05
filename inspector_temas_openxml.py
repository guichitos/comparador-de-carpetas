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
    target_tag_plain = TARGET_TAG.split(":")[-1]

    for element in root.iter():
        tag_without_ns = element.tag.split("}", maxsplit=1)[-1]
        if tag_without_ns not in (TARGET_TAG, target_tag_plain):
            continue

        theme_family = next(
            (
                child
                for child in element.iter()
                if child.tag.split("}", maxsplit=1)[-1] == "themeFamily"
            ),
            None,
        )

        if theme_family is not None:
            matches.append(ET.tostring(theme_family, encoding="unicode"))
        else:
            matches.append(ET.tostring(element, encoding="unicode"))

    return matches


def extract_theme_families(file_path: str) -> list[dict[str, str | None]]:
    """Extrae los valores de ``<themeFamily>`` de un ``theme1.xml``.

    Se devuelven diccionarios con los atributos ``id`` y ``vid`` para poder
    validar coincidencias con ``themeVariantManager.xml``.
    """

    try:
        tree = ET.parse(file_path)
    except ET.ParseError as exc:
        raise SystemExit(f"No se pudo parsear {file_path}: {exc}") from exc

    root = tree.getroot()
    families: list[dict[str, str | None]] = []

    for element in root.iter():
        tag_without_ns = element.tag.split("}", maxsplit=1)[-1]
        if tag_without_ns != "themeFamily":
            continue

        families.append(
            {
                "name": element.get("name"),
                "id": element.get("id"),
                "vid": element.get("vid"),
                "source": file_path,
            }
        )

    return families


def extract_variant_vids(file_path: str) -> list[dict[str, str | None]]:
    """Obtiene los ``vid`` de ``<themeVariant>`` en ``themeVariantManager.xml``."""

    try:
        tree = ET.parse(file_path)
    except ET.ParseError as exc:
        raise SystemExit(f"No se pudo parsear {file_path}: {exc}") from exc

    root = tree.getroot()
    variants: list[dict[str, str | None]] = []

    for element in root.iter():
        tag_without_ns = element.tag.split("}", maxsplit=1)[-1]
        if tag_without_ns != "themeVariant":
            continue

        variants.append(
            {
                "name": element.get("name"),
                "vid": element.get("vid"),
                "rel_id": element.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"),
            }
        )

    return variants


def resolve_relationship_target(rels_path: str, target: str, package_root: str | None) -> str:
    """Resuelve un ``Target`` de relaciones a una ruta absoluta en disco."""

    rels_dir = os.path.dirname(rels_path)

    if rels_dir.endswith("_rels"):
        base_dir = os.path.dirname(rels_dir)
    else:
        base_dir = rels_dir

    if target.startswith("/"):
        if package_root:
            return os.path.normpath(os.path.join(package_root, target.lstrip("/")))
        return os.path.normpath(os.path.join(base_dir, target.lstrip("/")))

    return os.path.normpath(os.path.join(base_dir, target))


def validate_variant_manager_links(variant_manager_path: str, package_root: str) -> None:
    """Comprueba que los ``Relationship`` de ``themeVariantManager.xml`` apunten a archivos existentes."""

    rels_path = os.path.join(
        os.path.dirname(variant_manager_path),
        "_rels",
        f"{os.path.basename(variant_manager_path)}.rels",
    )

    print("\nVerificación de vínculos de themeVariantManager.xml")
    if not os.path.exists(rels_path):
        print("No se encontró el archivo de relaciones correspondiente.")
        return

    try:
        tree = ET.parse(rels_path)
    except ET.ParseError as exc:
        print(f"No se pudo parsear {rels_path}: {exc}")
        return

    root = tree.getroot()
    relationships = root.findall(".//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")

    if not relationships:
        print("No se encontraron relaciones en el archivo.")
        return

    for relationship in relationships:
        rel_id = relationship.get("Id", "(sin Id)")
        target = relationship.get("Target")

        if not target:
            print(f"[ADVERTENCIA] La relación {rel_id} no tiene atributo Target.")
            continue

        resolved = resolve_relationship_target(rels_path, target, package_root)
        if os.path.exists(resolved):
            print(f"[OK] {rel_id}: archivo encontrado en {resolved}")
        else:
            print(f"[ERROR] {rel_id}: el archivo referenciado no existe ({resolved})")


def validate_variant_vids(variants: list[dict[str, str | None]], theme_families: list[dict[str, str | None]]) -> None:
    """Valida que cada ``vid`` de ``themeVariantManager.xml`` exista de forma única en los temas."""

    print("\nVerificación de correspondencia de VID entre themeVariantManager.xml y los themes")

    if not variants:
        print("No se encontraron entradas de themeVariant para validar.")
        return

    family_by_vid: dict[str | None, list[dict[str, str | None]]] = {}
    for family in theme_families:
        family_by_vid.setdefault(family.get("vid"), []).append(family)

    for variant in variants:
        vid = variant.get("vid")
        linked_families = family_by_vid.get(vid, [])

        if not linked_families:
            print(f"[ERROR] El VID {vid} no aparece en ningún theme1.xml.")
            continue

        if len(linked_families) > 1:
            sources = ", ".join((family.get("source") or "") for family in linked_families)
            print(f"[ERROR] El VID {vid} aparece repetido en varios temas: {sources}")
            continue

        print(
            f"[OK] El VID {vid} de themeVariantManager.xml coincide con el theme '"
            f"{linked_families[0].get('name')}' en {linked_families[0].get('source')}"
        )


def validate_theme_ids(theme_families: list[dict[str, str | None]]) -> None:
    """Comprueba que todos los ``id`` de ``themeFamily`` sean iguales entre sí."""

    print("\nVerificación de ID entre todos los theme1.xml")

    if not theme_families:
        print("No se encontraron entradas de themeFamily para validar.")
        return

    sources_by_id: dict[str | None, list[str]] = {}
    for family in theme_families:
        theme_id = family.get("id")
        sources_by_id.setdefault(theme_id, []).append(family.get("source") or "(origen desconocido)")

    if len(sources_by_id) == 1:
        only_id = next(iter(sources_by_id))
        print(f"[OK] Todos los theme1.xml comparten el mismo id: {only_id}")
        return

    print("[ERROR] Se encontraron IDs distintos entre los theme1.xml:")
    for theme_id, sources in sources_by_id.items():
        print(f"  - id {theme_id}: {', '.join(sources)}")


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
    all_theme_families: list[dict[str, str | None]] = []
    for theme_files in find_theme_files(base_dir):
        found = True
        contents = get_target_elements(theme_files.theme_path)
        all_theme_families.extend(extract_theme_families(theme_files.theme_path))
        if not contents:
            print(
                f"Tema sin {TARGET_TAG}: {theme_files.theme_path}",
            )
        else:
            for content in contents:
                print(f"{content}  | origen: {theme_files.theme_path}")

        if variant_manager_path is None and theme_files.variant_manager_path:
            variant_manager_path = theme_files.variant_manager_path
        print()

    if not found:
        print("No se encontraron carpetas theme/theme con un theme1.xml en la ruta indicada.")
    elif variant_manager_path:
        print("Contenido de themeVariantManager.xml:")
        print(read_xml_as_string(variant_manager_path))

        variants = extract_variant_vids(variant_manager_path)
        validate_variant_vids(variants, all_theme_families)
        validate_variant_manager_links(variant_manager_path, base_dir)
        validate_theme_ids(all_theme_families)
    else:
        print("No se encontró themeVariantManager.xml en la carpeta.")
        validate_theme_ids(all_theme_families)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
