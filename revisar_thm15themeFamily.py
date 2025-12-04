"""Validador para los enlaces de [Content_Types].xml en paquetes OpenXML.

El script permite seleccionar la carpeta raíz del paquete y luego elegir un
archivo [Content_Types].xml. Verifica que cada etiqueta <Default> y <Override>
cuente con sus atributos requeridos y que todos los PartName referenciados
apuntan a archivos existentes dentro del paquete. Además, si se encuentra el
recurso ``themeVariantManager.xml`` dentro de los overrides, se imprime su
contenido para facilitar la inspección.
"""

import os
import xml.etree.ElementTree as ET
from tkinter import Tk, filedialog


NS_TYPES = "{http://schemas.openxmlformats.org/package/2006/content-types}"


def resolve_part_path(base_dir: str, part_name: str) -> str:
    """Convierte un PartName en una ruta absoluta dentro del paquete."""
    normalized = part_name.lstrip("/\\")
    return os.path.normpath(os.path.join(base_dir, normalized))


def validate_content_types(path: str, base_dir: str) -> list[str]:
    print(f"\n[INFO] Iniciando validación del archivo: {os.path.basename(path)}")

    errors: list[str] = []

    print("[CHECK] Verificando si el XML está bien formado...")
    try:
        tree = ET.parse(path)
        print("[OK] XML bien formado.")
    except ET.ParseError as exc:
        message = f"[ERROR XML] Archivo mal formado: {exc}"
        print(message)
        errors.append(message)
        return errors

    root = tree.getroot()

    defaults = root.findall(f"{NS_TYPES}Default")
    overrides = root.findall(f"{NS_TYPES}Override")

    print(f"[INFO] Se encontraron {len(defaults)} elementos <Default> y {len(overrides)} elementos <Override>.")

    print("\n[INFO] Validando elementos <Default>...")
    extensions_seen: set[str] = set()
    for idx, default in enumerate(defaults, start=1):
        print(f"\n--- Verificando <Default> #{idx} ---")
        extension = default.get("Extension")
        content_type = default.get("ContentType")

        if not extension:
            msg = "[ERROR] El elemento <Default> no tiene atributo Extension."
            print(msg)
            errors.append(msg)
        else:
            print(f"[OK] Extension presente: {extension}")
            if extension in extensions_seen:
                msg = f"[ERROR] Extension duplicada: {extension}"
                print(msg)
                errors.append(msg)
            else:
                extensions_seen.add(extension)
                print("[OK] Extension es única.")

        if not content_type:
            msg = "[ERROR] El elemento <Default> no tiene atributo ContentType."
            print(msg)
            errors.append(msg)
        else:
            print(f"[OK] ContentType presente: {content_type}")

    print("\n[INFO] Validando elementos <Override>...")
    partnames_seen: set[str] = set()
    theme_variant_part: str | None = None
    for idx, override in enumerate(overrides, start=1):
        print(f"\n--- Verificando <Override> #{idx} ---")
        part_name = override.get("PartName")
        content_type = override.get("ContentType")

        if not part_name:
            msg = "[ERROR] El elemento <Override> no tiene atributo PartName."
            print(msg)
            errors.append(msg)
        else:
            if part_name.lower().endswith("themevariantmanager.xml"):
                theme_variant_part = part_name
            print(f"[OK] PartName presente: {part_name}")
            if part_name in partnames_seen:
                msg = f"[ERROR] PartName duplicado: {part_name}"
                print(msg)
                errors.append(msg)
            else:
                partnames_seen.add(part_name)
                print("[OK] PartName es único.")

            resolved_path = resolve_part_path(base_dir, part_name)
            print(f"[CHECK] Verificando existencia del archivo: {resolved_path}")

            if os.path.exists(resolved_path):
                print("[OK] El archivo referenciado SÍ existe.")
            else:
                msg = f"[ERROR] El archivo referenciado NO existe: {resolved_path}"
                print(msg)
                errors.append(msg)

        if not content_type:
            msg = "[ERROR] El elemento <Override> no tiene atributo ContentType."
            print(msg)
            errors.append(msg)
        else:
            print(f"[OK] ContentType presente: {content_type}")

    print("\n===========================================")
    print("[RESULTADO FINAL]")

    if not errors:
        print("[OK] No se encontraron errores en este archivo.")
        errors.append("[OK] No se encontraron errores.")
    else:
        print(f"[ERRORES] Se encontraron {len(errors)} problema(s).")

    if theme_variant_part:
        print_theme_variant_manager(base_dir, theme_variant_part)
    else:
        print(
            "\n[INFO] No se encontró una entrada para themeVariantManager.xml en <Override>."
        )

    print("===========================================\n")
    return errors


def print_theme_variant_manager(base_dir: str, part_name: str) -> None:
    """Muestra el contenido del archivo themeVariantManager.xml si existe."""

    resolved_path = resolve_part_path(base_dir, part_name)
    print(f"\n[INFO] Ubicación detectada para themeVariantManager.xml: {resolved_path}")

    if not os.path.exists(resolved_path):
        print("[ERROR] El archivo themeVariantManager.xml no existe en el paquete.")
        return

    print("[CHECK] Leyendo contenido de themeVariantManager.xml...")
    try:
        with open(resolved_path, "r", encoding="utf-8") as file:
            content = file.read()
    except UnicodeDecodeError:
        print(
            "[WARNING] No fue posible decodificar el archivo con UTF-8. Se leerá como binario."
        )
        with open(resolved_path, "rb") as file:
            content = file.read().decode(errors="replace")

    print("\n======= Contenido de themeVariantManager.xml =======")
    print(content)
    print("======= Fin de themeVariantManager.xml =======\n")


def main() -> None:
    Tk().withdraw()

    base_dir = filedialog.askdirectory(
        title="Seleccionar carpeta raíz del paquete (donde está [Content_Types].xml)"
    )

    if not base_dir:
        print("No se seleccionó la carpeta raíz. Operación cancelada.")
        return

    xml_path = filedialog.askopenfilename(
        title="Seleccionar archivo [Content_Types].xml",
        filetypes=[("Content Types", "[Content_Types].xml"), ("Todos los archivos", "*.*")],
        initialdir=base_dir,
    )

    if not xml_path:
        print("No se seleccionó ningún archivo. Operación cancelada.")
        return

    validate_content_types(xml_path, base_dir)


if __name__ == "__main__":
    main()
