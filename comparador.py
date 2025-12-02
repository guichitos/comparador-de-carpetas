"""Aplicación gráfica simple para comparar el contenido de dos carpetas.

El programa usa Tkinter para permitir que el usuario seleccione dos
carpetas y presenta sus árboles de directorios lado a lado. Cada nodo
muestra su estado respecto a la carpeta opuesta (solo en un lado,
coincide o es diferente en tamaño) y el tamaño para los archivos cuando
está disponible.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk


class FolderComparator(tk.Tk):
    """Ventana principal que gestiona la comparación de carpetas."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Comparador de carpetas")
        self.geometry("1050x650")

        self.left_path = tk.StringVar()
        self.right_path = tk.StringVar()

        self.left_item_paths: dict[str, str] = {}
        self.right_item_paths: dict[str, str] = {}
        self.left_base_path: str | None = None
        self.right_base_path: str | None = None

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
        left_container.rowconfigure(0, weight=3)
        left_container.rowconfigure(1, weight=1)
        left_container.columnconfigure(0, weight=1)

        right_container = ttk.Frame(trees_frame)
        right_container.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        right_container.rowconfigure(0, weight=3)
        right_container.rowconfigure(1, weight=1)
        right_container.columnconfigure(0, weight=1)

        self.left_tree = self._create_tree(left_container)
        self.right_tree = self._create_tree(right_container)

        self.left_preview = self._create_preview(left_container)
        self.right_preview = self._create_preview(right_container)

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

        tree.bind("<<TreeviewSelect>>", self._on_selection_change)
        return tree

    def _create_preview(self, master: tk.Misc) -> scrolledtext.ScrolledText:
        """Crea un área de texto para previsualizar archivos."""

        preview = scrolledtext.ScrolledText(master, height=8, wrap="word")
        preview.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        preview.configure(state="disabled")
        return preview

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
        """Escanea las carpetas seleccionadas y actualiza cada árbol por separado."""
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

        self.left_base_path = left_dir
        self.right_base_path = right_dir

        self.left_item_paths = {}
        self.right_item_paths = {}

        self._populate_tree(
            tree=self.left_tree,
            base_path=left_dir,
            entries=left_entries,
            path_store=self.left_item_paths,
        )
        self._populate_tree(
            tree=self.right_tree,
            base_path=right_dir,
            entries=right_entries,
            path_store=self.right_item_paths,
        )

        self._clear_preview(self.left_preview)
        self._clear_preview(self.right_preview)

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

    def _populate_tree(
        self,
        tree: ttk.Treeview,
        base_path: str,
        entries: dict[str, dict[str, object]],
        path_store: dict[str, str],
    ) -> None:
        """Llena el Treeview con las entradas de un solo directorio."""
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
        path_store.clear()
        path_store[root_id] = ""
        sorted_paths = sorted(
            (path for path in entries if path != ""), key=lambda p: (p.count(os.sep), p)
        )

        for path in sorted_paths:
            parent_path = os.path.dirname(path)
            name = os.path.basename(path)
            parent_id = parent_ids.get(parent_path, root_id)

            info = entries[path]
            item_type = "Carpeta" if info["type"] == "dir" else "Archivo"

            if info["type"] == "file":
                size_value = info.get("size")
                size_display = f"{size_value} B" if isinstance(size_value, int) else "-"
            else:
                size_display = "-"

            node_id = tree.insert(
                parent_id,
                "end",
                text=name,
                values=("", item_type, size_display),
                open=False,
            )
            parent_ids[path] = node_id
            path_store[node_id] = path

    def _on_selection_change(self, event: tk.Event) -> None:
        """Muestra el archivo seleccionado en el panel inferior correspondiente."""

        tree = event.widget
        if tree not in (self.left_tree, self.right_tree):
            return

        item_id = tree.selection()
        if not item_id:
            return
        selected_id = item_id[0]

        if tree is self.left_tree:
            base_path = self.left_base_path
            path_store = self.left_item_paths
            preview = self.left_preview
        else:
            base_path = self.right_base_path
            path_store = self.right_item_paths
            preview = self.right_preview

        if base_path is None:
            return

        rel_path = path_store.get(selected_id)
        if rel_path is None:
            self._clear_preview(preview)
            return

        full_path = os.path.join(base_path, rel_path) if rel_path else base_path
        if os.path.isdir(full_path):
            self._show_message(preview, "Seleccione un archivo para previsualizar su contenido.")
            return

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as file:
                content = file.read()
        except OSError as exc:
            self._show_message(preview, f"No se pudo leer el archivo: {exc}")
            return

        self._set_preview_text(preview, content)

    def _clear_preview(self, widget: scrolledtext.ScrolledText) -> None:
        """Limpia el texto de la previsualización."""

        self._set_preview_text(widget, "")

    def _show_message(self, widget: scrolledtext.ScrolledText, message: str) -> None:
        """Muestra un mensaje informativo en el panel de previsualización."""

        self._set_preview_text(widget, message)

    def _set_preview_text(self, widget: scrolledtext.ScrolledText, text: str) -> None:
        """Actualiza el contenido del cuadro de texto de forma segura."""

        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")


def main() -> None:
    app = FolderComparator()
    app.mainloop()


if __name__ == "__main__":
    main()
