"""Aplicación gráfica simple para comparar el contenido de dos carpetas.

El programa usa Tkinter para permitir que el usuario seleccione dos
carpetas y presenta sus árboles de directorios lado a lado. Cada nodo
muestra su estado respecto a la carpeta opuesta (solo en un lado,
coincide o es diferente en tamaño) y el tamaño para los archivos cuando
está disponible.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class FolderComparator(tk.Tk):
    """Ventana principal que gestiona la comparación de carpetas."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Comparador de carpetas")
        self.geometry("1050x650")

        self.left_path = tk.StringVar()
        self.right_path = tk.StringVar()

        self._build_layout()

    def _build_layout(self) -> None:
        """Construye la interfaz de usuario."""
        path_frame = ttk.Frame(self, padding=10)
        path_frame.grid(row=0, column=0, sticky="ew")
        path_frame.columnconfigure(1, weight=1)
        path_frame.columnconfigure(4, weight=1)

        ttk.Label(path_frame, text="Carpeta izquierda:").grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        left_entry = ttk.Entry(path_frame, textvariable=self.left_path)
        left_entry.grid(row=0, column=1, sticky="ew")
        ttk.Button(
            path_frame,
            text="Seleccionar",
            command=lambda: self._select_directory("left"),
        ).grid(row=0, column=2, padx=6)

        ttk.Label(path_frame, text="Carpeta derecha:").grid(
            row=0, column=3, sticky="w", padx=(12, 6)
        )
        right_entry = ttk.Entry(path_frame, textvariable=self.right_path)
        right_entry.grid(row=0, column=4, sticky="ew")
        ttk.Button(
            path_frame,
            text="Seleccionar",
            command=lambda: self._select_directory("right"),
        ).grid(row=0, column=5, padx=6)

        trees_frame = ttk.Frame(self, padding=10)
        trees_frame.grid(row=1, column=0, sticky="nsew")
        trees_frame.columnconfigure(0, weight=1)
        trees_frame.columnconfigure(1, weight=1)
        trees_frame.rowconfigure(1, weight=1)

        ttk.Label(trees_frame, text="Carpeta izquierda", font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(trees_frame, text="Carpeta derecha", font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=1, sticky="w"
        )

        left_container = ttk.Frame(trees_frame)
        left_container.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        left_container.rowconfigure(0, weight=1)
        left_container.columnconfigure(0, weight=1)

        right_container = ttk.Frame(trees_frame)
        right_container.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        right_container.rowconfigure(0, weight=1)
        right_container.columnconfigure(0, weight=1)

        self.left_tree = self._create_tree(left_container)
        self.right_tree = self._create_tree(right_container)

        actions_frame = ttk.Frame(self, padding=10)
        actions_frame.grid(row=2, column=0, sticky="ew")
        ttk.Button(actions_frame, text="Comparar ahora", command=self.update_comparison).pack(
            anchor="e"
        )

        self.rowconfigure(1, weight=1)

    def _create_tree(self, master: tk.Misc) -> ttk.Treeview:
        """Crea un Treeview con columnas de estado, tipo y tamaño."""
        columns = ("estado", "tipo", "tamano")
        tree = ttk.Treeview(master, columns=columns, show="tree headings")
        tree.heading("#0", text="Elemento", anchor="w")
        tree.heading("estado", text="Estado", anchor="w")
        tree.heading("tipo", text="Tipo", anchor="w")
        tree.heading("tamano", text="Tamaño", anchor="e")

        tree.column("#0", width=280, stretch=True)
        tree.column("estado", width=120, anchor="w")
        tree.column("tipo", width=100, anchor="w")
        tree.column("tamano", width=100, anchor="e")

        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(master, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")
        return tree

    def _select_directory(self, side: str) -> None:
        """Abre un diálogo para seleccionar directorios y actualiza la vista."""
        selected = filedialog.askdirectory()
        if not selected:
            return
        if side == "left":
            self.left_path.set(selected)
        else:
            self.right_path.set(selected)
        self.update_comparison()

    def update_comparison(self) -> None:
        """Escanea las carpetas seleccionadas y actualiza los árboles."""
        left_dir = self.left_path.get()
        right_dir = self.right_path.get()

        if not left_dir or not right_dir:
            messagebox.showinfo(
                "Seleccione carpetas",
                "Seleccione tanto la carpeta izquierda como la derecha para comparar.",
            )
            return

        left_entries = self._scan_directory(left_dir)
        right_entries = self._scan_directory(right_dir)
        combined, statuses = self._compare_entries(left_entries, right_entries)

        self._populate_tree(
            tree=self.left_tree,
            base_path=left_dir,
            side_entries=left_entries,
            combined=combined,
            statuses=statuses["left"],
            side="left",
        )
        self._populate_tree(
            tree=self.right_tree,
            base_path=right_dir,
            side_entries=right_entries,
            combined=combined,
            statuses=statuses["right"],
            side="right",
        )

    def _scan_directory(self, base_path: str) -> dict[str, dict[str, object]]:
        """Genera un diccionario con todos los elementos dentro de un directorio."""
        entries: dict[str, dict[str, object]] = {"": {"type": "dir"}}
        for current, dirs, files in os.walk(base_path):
            rel_dir = os.path.relpath(current, base_path)
            rel_dir = "" if rel_dir == "." else rel_dir
            for directory in dirs:
                rel_path = os.path.join(rel_dir, directory)
                entries[rel_path] = {"type": "dir"}
            for filename in files:
                rel_path = os.path.join(rel_dir, filename)
                file_path = os.path.join(current, filename)
                try:
                    size = os.path.getsize(file_path)
                except OSError:
                    size = None
                entries[rel_path] = {"type": "file", "size": size}
        return entries

    def _compare_entries(
        self, left_entries: dict[str, dict[str, object]], right_entries: dict[str, dict[str, object]]
    ) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, str]]]:
        """Compara dos diccionarios de entradas y devuelve datos combinados y estados."""
        combined: dict[str, dict[str, object]] = {}
        statuses: dict[str, dict[str, str]] = {"left": {}, "right": {}}

        for path in sorted(set(left_entries) | set(right_entries)):
            left_info = left_entries.get(path)
            right_info = right_entries.get(path)
            info = left_info or right_info
            if info is None:
                continue

            entry_type = info["type"]
            combined[path] = {"type": entry_type}

            if entry_type == "file":
                size_left = left_info.get("size") if left_info else None
                size_right = right_info.get("size") if right_info else None
                combined[path]["size_left"] = size_left
                combined[path]["size_right"] = size_right

                if left_info and right_info:
                    status = "Coincide" if size_left == size_right else "Diferente"
                    statuses["left"][path] = status
                    statuses["right"][path] = status
                elif left_info:
                    statuses["left"][path] = "Solo izquierda"
                    statuses["right"][path] = "No existe"
                else:
                    statuses["left"][path] = "No existe"
                    statuses["right"][path] = "Solo derecha"
            else:
                if left_info and right_info:
                    status = "Coincide"
                    statuses["left"][path] = status
                    statuses["right"][path] = status
                elif left_info:
                    statuses["left"][path] = "Solo izquierda"
                    statuses["right"][path] = "No existe"
                else:
                    statuses["left"][path] = "No existe"
                    statuses["right"][path] = "Solo derecha"

        return combined, statuses

    def _populate_tree(
        self,
        tree: ttk.Treeview,
        base_path: str,
        side_entries: dict[str, dict[str, object]],
        combined: dict[str, dict[str, object]],
        statuses: dict[str, str],
        side: str,
    ) -> None:
        """Llena el Treeview con los resultados de comparación."""
        tree.delete(*tree.get_children())

        root_label = os.path.basename(base_path.rstrip(os.sep)) or base_path
        root_id = tree.insert(
            "",
            "end",
            text=root_label,
            values=("Seleccionada", "Carpeta", "-"),
            open=True,
        )

        parent_ids: dict[str, str] = {"": root_id}
        sorted_paths = sorted(
            (path for path in combined if path != ""), key=lambda p: (p.count(os.sep), p)
        )

        for path in sorted_paths:
            parent_path = os.path.dirname(path)
            name = os.path.basename(path)
            parent_id = parent_ids.get(parent_path, root_id)

            info = combined[path]
            entry_info = side_entries.get(path)
            status = statuses.get(path, "")
            item_type = "Carpeta" if info["type"] == "dir" else "Archivo"

            if info["type"] == "file":
                size_value = (
                    entry_info.get("size")
                    if entry_info
                    else info.get("size_left")
                    if side == "left"
                    else info.get("size_right")
                )
                size_display = f"{size_value} B" if isinstance(size_value, int) else "-"
            else:
                size_display = "-"

            node_id = tree.insert(
                parent_id,
                "end",
                text=name,
                values=(status, item_type, size_display),
                open=False,
            )
            parent_ids[path] = node_id


def main() -> None:
    app = FolderComparator()
    app.mainloop()


if __name__ == "__main__":
    main()
