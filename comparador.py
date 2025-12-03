"""Aplicación gráfica simple para comparar el contenido de dos carpetas.

El programa usa Tkinter para permitir que el usuario seleccione dos
carpetas y presenta sus árboles de directorios lado a lado. Cada nodo
muestra su estado respecto a la carpeta opuesta (solo en un lado,
coincide o es diferente en tamaño) y el tamaño para los archivos cuando
está disponible.
"""

import json
import os
import tkinter as tk
from typing import cast
from tkinter import filedialog, messagebox, scrolledtext, ttk


class FolderComparator(tk.Tk):
    """Ventana principal que gestiona la comparación de carpetas."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Comparador de carpetas")
        self.geometry("1050x650")

        self.left_path = tk.StringVar()
        self.right_path = tk.StringVar()

        self.left_title = tk.StringVar(value="Carpeta izquierda (sin seleccionar)")
        self.right_title = tk.StringVar(value="Carpeta derecha (sin seleccionar)")

        self.left_item_paths: dict[str, str] = {}
        self.right_item_paths: dict[str, str] = {}
        self.left_base_path: str | None = None
        self.right_base_path: str | None = None
        self.comparison_data: dict[str, dict[str, object]] = {}
        self.difference_paths: set[str] = set()
        self.show_differences_only = tk.BooleanVar(value=False)
        self.debug_enabled = tk.BooleanVar(value=True)
        self._debug_sample_limit = 15

        self._last_left_entries: dict[str, dict[str, object]] | None = None
        self._last_right_entries: dict[str, dict[str, object]] | None = None

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

        ttk.Label(
            trees_frame,
            textvariable=self.left_title,
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            trees_frame,
            textvariable=self.right_title,
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=0, column=1, sticky="w")

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
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)
        actions_frame.columnconfigure(2, weight=1)

        ttk.Button(
            actions_frame,
            text="Exportar izquierda",
            command=lambda: self._export_directory("left"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            actions_frame,
            text="Exportar derecha",
            command=lambda: self._export_directory("right"),
        ).grid(row=0, column=1, sticky="w")
        ttk.Button(actions_frame, text="Comparar ahora", command=self.update_comparison).grid(
            row=0, column=2, sticky="e"
        )

        ttk.Checkbutton(
            actions_frame,
            text="Mostrar solo diferencias",
            variable=self.show_differences_only,
            command=self._on_filter_change,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

        debug_frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        debug_frame.grid(row=3, column=0, sticky="nsew")
        debug_frame.columnconfigure(0, weight=1)
        debug_frame.rowconfigure(1, weight=1)

        controls = ttk.Frame(debug_frame)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(2, weight=1)

        ttk.Label(controls, text="Depuración:").grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(
            controls,
            text="Mostrar logs en la app",
            variable=self.debug_enabled,
        ).grid(row=0, column=1, sticky="w", padx=(6, 0))
        ttk.Button(controls, text="Limpiar", command=self._clear_debug_log).grid(
            row=0, column=3, sticky="e"
        )

        self.debug_text = scrolledtext.ScrolledText(debug_frame, height=6, wrap="word")
        self.debug_text.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self.debug_text.configure(state="disabled")

        self.rowconfigure(1, weight=1)
        self.rowconfigure(3, weight=1)

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
        self._update_tree_title(side)
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

        if not os.path.isdir(left_dir) or not os.path.isdir(right_dir):
            messagebox.showerror(
                "Ruta inválida",
                "Verifique que ambas rutas correspondan a carpetas existentes.",
            )
            return

        self._update_tree_title("left")
        self._update_tree_title("right")

        left_entries = self._scan_directory(left_dir)
        right_entries = self._scan_directory(right_dir)

        self.left_base_path = left_dir
        self.right_base_path = right_dir

        self.left_item_paths = {}
        self.right_item_paths = {}

        self._last_left_entries = left_entries
        self._last_right_entries = right_entries
        self._log_debug(
            f"Escaneo completado. Izquierda: {len(left_entries)} entradas, "
            f"Derecha: {len(right_entries)} entradas."
        )
        self.comparison_data, self.difference_paths = self._build_comparison(
            left_entries, right_entries
        )

        self._refresh_trees()

        self._clear_preview(self.left_preview)
        self._clear_preview(self.right_preview)

    def _on_filter_change(self) -> None:
        """Aplica el filtro sin requerir un reescaneo si ya hay datos cargados."""

        if self._last_left_entries is None or self._last_right_entries is None:
            self.update_comparison()
            return

        self._log_debug(
            "Cambio de filtro: Mostrar solo diferencias = "
            f"{self.show_differences_only.get()}"
        )

        self._refresh_trees()

    def _refresh_trees(self) -> None:
        """Puebla ambos árboles usando los datos de la última comparación."""

        if self._last_left_entries is None or self._last_right_entries is None:
            return

        filtered_left = self._filter_entries_for_display(self._last_left_entries)
        filtered_right = self._filter_entries_for_display(self._last_right_entries)

        self._populate_tree(
            tree=self.left_tree,
            base_path=self.left_base_path or "",
            entries=filtered_left,
            path_store=self.left_item_paths,
            side="left",
        )
        self._populate_tree(
            tree=self.right_tree,
            base_path=self.right_base_path or "",
            entries=filtered_right,
            path_store=self.right_item_paths,
            side="right",
        )

    def _filter_entries_for_display(
        self, entries: dict[str, dict[str, object]]
    ) -> dict[str, dict[str, object]]:
        """Devuelve las entradas ya comparadas respetando el filtro de diferencias."""

        if not self.show_differences_only.get():
            self._log_debug(
                f"Filtro desactivado: se muestran todas las {len(entries)} entradas."
            )
            return entries

        filtered: dict[str, dict[str, object]] = {}
        skipped_samples: list[str] = []
        for path, info in entries.items():
            if path == "" or self._is_path_relevant(path):
                filtered[path] = info
            elif len(skipped_samples) < self._debug_sample_limit:
                status = self.comparison_data.get(path, {})
                skipped_samples.append(f"{path} -> {status}")

        self._log_debug(
            "Filtro activado: conservadas "
            f"{len(filtered)} de {len(entries)} entradas."
        )
        if skipped_samples:
            self._log_debug(
                "Ejemplos de rutas omitidas por coincidir en ambos lados:\n"
                + "\n".join(skipped_samples)
            )
        return filtered

    def _is_path_relevant(self, path: str) -> bool:
        """Indica si una ruta debe mostrarse cuando se piden solo diferencias."""

        comparison_info = self.comparison_data.get(path)
        differs = bool(comparison_info and comparison_info.get("differs"))
        return differs or path in self.difference_paths

    def _update_tree_title(self, side: str) -> None:
        """Muestra el nombre de la carpeta seleccionada sobre el árbol correspondiente."""

        if side == "left":
            path = self.left_path.get()
            title_var = self.left_title
            label = "Carpeta izquierda"
        else:
            path = self.right_path.get()
            title_var = self.right_title
            label = "Carpeta derecha"

        if path:
            folder_name = os.path.basename(path.rstrip(os.sep)) or path
            title_var.set(f"{label}: {folder_name}")
        else:
            title_var.set(f"{label} (sin seleccionar)")

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
        side: str,
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
            if self.show_differences_only.get() and not self._is_path_relevant(path):
                continue

            parent_path = os.path.dirname(path)
            name = os.path.basename(path)
            parent_id = parent_ids.get(parent_path, root_id)

            info = entries[path]
            item_type = "Carpeta" if info["type"] == "dir" else "Archivo"

            status = self._get_status_for_side(path, side)
            if info["type"] == "file":
                size_value = info.get("size")
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
            path_store[node_id] = path

        self._log_debug(
            f"Árbol {side}: {len(path_store)} nodos insertados (incluye la raíz)."
        )

    def _get_status_for_side(self, path: str, side: str) -> str:
        """Devuelve el estado calculado para un elemento en el árbol indicado."""

        data = self.comparison_data.get(path)
        if not data:
            return ""

        status = data.get(f"status_{side}")
        return status if isinstance(status, str) else ""

    def _build_comparison(
        self,
        left_entries: dict[str, dict[str, object]],
        right_entries: dict[str, dict[str, object]],
    ) -> tuple[dict[str, dict[str, object]], set[str]]:
        """Compara dos diccionarios de entradas y marca diferencias por ruta."""

        comparison: dict[str, dict[str, object]] = {}
        differing_paths: set[str] = set()
        all_paths = set(left_entries) | set(right_entries)

        for path in all_paths:
            left_info = left_entries.get(path)
            right_info = right_entries.get(path)

            status_left, status_right, differs = self._determine_status(left_info, right_info)
            comparison[path] = {
                "status_left": status_left,
                "status_right": status_right,
                "differs": differs,
            }

            if differs:
                differing_paths.add(path)

        for path in list(differing_paths):
            parent = self._parent_path(path)
            while parent is not None:
                differing_paths.add(parent)
                parent = self._parent_path(parent)

        sample = sorted(differing_paths)[: self._debug_sample_limit]
        self._log_debug(
            f"Comparación calculada: {len(comparison)} rutas evaluadas, "
            f"{len(differing_paths)} marcadas como relevantes. "
            f"Ejemplos: {sample}"
        )
        return comparison, differing_paths

    def _determine_status(
        self,
        left_info: dict[str, object] | None,
        right_info: dict[str, object] | None,
    ) -> tuple[str, str, bool]:
        """Calcula el estado de cada lado para una ruta determinada."""

        if left_info and right_info:
            if left_info["type"] != right_info["type"]:
                return "Tipo distinto", "Tipo distinto", True

            if left_info["type"] == "file":
                left_size = left_info.get("size")
                right_size = right_info.get("size")

                if isinstance(left_size, int) and isinstance(right_size, int):
                    if left_size == right_size:
                        return "Coincide", "Coincide", False
                    return "Tamaño diferente", "Tamaño diferente", True

                return "Coincide", "Coincide", False

            return "Coincide", "Coincide", False

        if left_info:
            return "Solo izquierda", "No existe", True

        if right_info:
            return "No existe", "Solo derecha", True

        return "", "", False

    def _parent_path(self, path: str) -> str | None:
        """Obtiene la ruta relativa del padre o None cuando es la raíz."""

        if not path:
            return None

        parent = os.path.dirname(path)
        return parent if parent != path else None

    def _clear_debug_log(self) -> None:
        """Borra el cuadro de log de depuración."""

        self.debug_text.configure(state="normal")
        self.debug_text.delete("1.0", tk.END)
        self.debug_text.configure(state="disabled")

    def _log_debug(self, message: str) -> None:
        """Envía mensajes de depuración al cuadro de texto y a la consola."""

        print(f"[DEBUG] {message}")
        if not self.debug_enabled.get():
            return

        self.debug_text.configure(state="normal")
        self.debug_text.insert(tk.END, message + "\n")
        self.debug_text.see(tk.END)
        self.debug_text.configure(state="disabled")

    def _on_selection_change(self, event: tk.Event) -> None:
        """Muestra el archivo seleccionado en el panel inferior correspondiente."""

        if not isinstance(event.widget, ttk.Treeview):
            return

        tree = cast(ttk.Treeview, event.widget)
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

    def _export_directory(self, side: str) -> None:
        """Exporta el contenido de una carpeta a un archivo JSON."""

        if side == "left":
            base_path = self.left_path.get()
            label = "izquierda"
        else:
            base_path = self.right_path.get()
            label = "derecha"

        if not base_path:
            messagebox.showinfo(
                "Seleccione carpeta",
                f"Seleccione la carpeta {label} antes de exportar su contenido.",
            )
            return

        if not os.path.isdir(base_path):
            messagebox.showerror(
                "Ruta inválida",
                f"La ruta de la carpeta {label} no existe o no es válida.",
            )
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")],
            initialfile=f"{os.path.basename(base_path) or 'carpeta'}.json",
            title="Guardar contenido como JSON",
        )
        if not save_path:
            return

        export_data = self._build_export_data(base_path)

        try:
            with open(save_path, "w", encoding="utf-8") as outfile:
                json.dump(export_data, outfile, ensure_ascii=False, indent=2)
        except OSError as exc:
            messagebox.showerror("Error al guardar", f"No se pudo guardar el archivo: {exc}")
            return

        messagebox.showinfo(
            "Exportación completada",
            f"Se exportó el contenido de la carpeta {label} a:\n{save_path}",
        )

    def _build_export_data(self, base_path: str) -> dict[str, object]:
        """Prepara la estructura JSON con el contenido de un directorio."""

        entries = self._scan_directory(base_path)
        export_entries = []
        for rel_path, info in sorted(entries.items()):
            export_entries.append(
                {
                    "ruta": rel_path or ".",
                    "tipo": "carpeta" if info["type"] == "dir" else "archivo",
                    "tamano": info.get("size") if info["type"] == "file" else None,
                }
            )

        return {
            "carpeta": base_path,
            "entradas": export_entries,
        }


def main() -> None:
    app = FolderComparator()
    app.mainloop()


if __name__ == "__main__":
    main()
