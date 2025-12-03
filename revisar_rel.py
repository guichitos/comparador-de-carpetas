import xml.etree.ElementTree as ET
from tkinter import Tk, filedialog
import os

def resolve_target_path(rels_path, target):
    """
    Convierte un Target relativo en una ruta absoluta real.
    Ejemplo:
        rels:  C:\tema\theme\_rels\slideLayout1.xml.rels
        target: ../slideMasters/slideMaster1.xml
    Resultado:
        C:\tema\theme\slideMasters\slideMaster1.xml
    """
    rels_dir = os.path.dirname(rels_path)

    # Carpeta padre de _rels (porque los targets se basan en la carpeta del XML original)
    if rels_dir.endswith("_rels"):
        base_dir = os.path.dirname(rels_dir)
    else:
        base_dir = rels_dir

    # Resolver rutas ../ y subcarpetas
    full_path = os.path.normpath(os.path.join(base_dir, target))
    return full_path


def validate_rels_file(path):
    print(f"\n[INFO] Iniciando validación del archivo: {os.path.basename(path)}")

    errors = []

    # 1. Validar XML
    print("[CHECK] Verificando si el XML está bien formado...")
    try:
        tree = ET.parse(path)
        print("[OK] XML bien formado.")
    except ET.ParseError as e:
        print(f"[ERROR XML] Archivo mal formado: {e}")
        errors.append(f"[ERROR XML] Archivo no válido: {e}")
        return errors

    root = tree.getroot()

    # Namespace
    NS_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"

    print("[CHECK] Extrayendo etiquetas <Relationship>...")
    rels = root.findall(f".//{NS_REL}Relationship")
    print(f"[INFO] Relaciones encontradas: {len(rels)}")

    print("\n[INFO] Iniciando verificaciones por relación...\n")
    ids = set()

    for idx, rel in enumerate(rels, start=1):
        print(f"\n--- Verificando relación #{idx} ---")

        rid = rel.get("Id")
        rtype = rel.get("Type")
        rtarget = rel.get("Target")

        # Verificación de Id
        print("[CHECK] Verificando Id...")
        if not rid:
            msg = "[ERROR] Hay una relación sin Id."
            print(msg)
            errors.append(msg)
        else:
            print(f"[OK] Id presente: {rid}")
            if rid in ids:
                msg = f"[ERROR] Id duplicado: {rid}"
                print(msg)
                errors.append(msg)
            else:
                ids.add(rid)
                print("[OK] Id es único.")

        # Verificación de Type
        print("[CHECK] Verificando Type...")
        if not rtype:
            msg = f"[ERROR] La relación {rid} no tiene Type."
            print(msg)
            errors.append(msg)
        else:
            print(f"[OK] Type presente: {rtype}")

        # Verificación de Target
        print("[CHECK] Verificando Target...")
        if not rtarget:
            msg = f"[ERROR] La relación {rid} no tiene Target."
            print(msg)
            errors.append(msg)
        else:
            print(f"[OK] Target presente: {rtarget}")

            #  NUEVO: verificar si el archivo Target realmente existe
            resolved_path = resolve_target_path(path, rtarget)
            print(f"[CHECK] Verificando existencia del archivo: {resolved_path}")

            if os.path.exists(resolved_path):
                print("[OK] El archivo referenciado SÍ existe.")
            else:
                msg = f"[ERROR] El archivo referenciado NO existe: {resolved_path}"
                print(msg)
                errors.append(msg)

    print("\n===========================================")
    print("[RESULTADO FINAL]")

    if not errors:
        print("[OK] No se encontraron errores en este archivo.")
        errors.append("[OK] No se encontraron errores.")
    else:
        print(f"[ERRORES] Se encontraron {len(errors)} problema(s).")

    print("===========================================\n")
    return errors


def main():
    Tk().withdraw()

    paths = filedialog.askopenfilenames(
        title="Seleccionar archivos .rels",
        filetypes=[("Archivos RELS", "*.rels"), ("Todos los archivos", "*.*")]
    )

    if not paths:
        print("Ningún archivo seleccionado.")
        return

    for path in paths:
        validate_rels_file(path)


if __name__ == "__main__":
    main()
