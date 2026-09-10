"""
Ventana principal de la interfaz gráfica con selector de archivos.
Versión completamente funcional con botón de limpiar.
"""
import tkinter as tk                                  # GUI base de Python
from tkinter import ttk, filedialog, messagebox, scrolledtext  # Widgets, diálogos y caja con scroll
from pathlib import Path                              # Rutas portables
import threading                                      # Ejecutar el análisis sin bloquear la GUI
import logging                                        # Logging interno

logger = logging.getLogger(__name__)                  # Logger del módulo


class MainWindow:
    """Ventana principal de la aplicación."""

    def __init__(self):
        # Ventana raíz de Tk (se crea en run()).
        self.root = None
        # Ruta del archivo .log seleccionado por el usuario.
        self.selected_file = None
        # Hilo donde corre el análisis (para no congelar la GUI).
        self.analysis_thread = None
        # Servicio de análisis (se crea perezosamente en el hilo).
        self.service = None
        # Contador para la animación de puntos suspensivos.
        self._progress_count = 0

    def run(self):
        """Ejecuta la interfaz gráfica."""
        # Crear la ventana principal de Tk.
        self.root = tk.Tk()
        self.root.title("Analizador de Logs con IA")
        self.root.geometry("900x700")              # Tamaño inicial
        self.root.minsize(800, 600)                # Tamaño mínimo

        # Construir todos los widgets de la ventana.
        self._create_widgets()

        # Centrar la ventana en la pantalla.
        self._center_window()

        # Arrancar el bucle de eventos de Tk.
        self.root.mainloop()

    def _create_widgets(self):
        """Crea todos los widgets de la interfaz."""
        # Frame principal con padding exterior.
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Título superior ---
        title_label = tk.Label(
            main_frame,
            text="📊 Analizador de Logs con IA",
            font=('Segoe UI', 18, 'bold'),
            bg='#f0f0f0',
            fg='#0078d4'
        )
        title_label.pack(pady=(0, 20))

        # --- Frame de selección de archivo ---
        file_frame = ttk.LabelFrame(main_frame, text="📁 Seleccionar Archivo", padding="15")
        file_frame.pack(fill=tk.X, pady=(0, 15))

        # Sub-frame para el entry + botón limpiar.
        entry_frame = ttk.Frame(file_frame)
        entry_frame.pack(fill=tk.X)

        # Entry donde se muestra la ruta seleccionada.
        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(
            entry_frame,
            textvariable=self.file_path_var,
            font=('Segoe UI', 9)
        )
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # Botón para limpiar todo.
        self.clear_btn = ttk.Button(
            entry_frame,
            text="🗑️ Limpiar",
            command=self._clear_all,
            width=20
        )
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Sub-frame para botones de navegación.
        nav_frame = ttk.Frame(file_frame)
        nav_frame.pack(fill=tk.X, pady=(10, 0))

        # Botón "Examinar..." (selector de archivos).
        self.select_btn = ttk.Button(
            nav_frame,
            text="📂 Examinar...",
            command=self._select_file,
            width=15
        )
        self.select_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Botón que abre el selector directamente en Descargas.
        self.downloads_btn = ttk.Button(
            nav_frame,
            text="📥 Descargas",
            command=self._open_downloads,
            width=15
        )
        self.downloads_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Botón que abre el selector en el directorio del proyecto.
        self.current_dir_btn = ttk.Button(
            nav_frame,
            text="📂 Carpeta actual",
            command=self._open_current_directory,
            width=15
        )
        self.current_dir_btn.pack(side=tk.LEFT)

        # Label de estado del archivo seleccionado.
        self.file_status = tk.Label(
            main_frame,
            text="ℹ️ Selecciona un archivo .log para analizar",
            font=('Segoe UI', 9),
            fg='#666666'
        )
        self.file_status.pack(anchor='w', pady=(5, 10))

        # --- Frame de configuración ---
        config_frame = ttk.LabelFrame(main_frame, text="⚙️ Configuración", padding="15")
        config_frame.pack(fill=tk.X, pady=(0, 15))

        # Checkbox: usar IA (Ollama) o no.
        self.use_ai_var = tk.BooleanVar(value=True)
        self.use_ai_check = ttk.Checkbutton(
            config_frame,
            text="Usar IA para análisis (Ollama)",
            variable=self.use_ai_var
        )
        self.use_ai_check.pack(anchor='w')

        # Checkbox: modo verbose.
        self.verbose_var = tk.BooleanVar(value=False)
        self.verbose_check = ttk.Checkbutton(
            config_frame,
            text="Modo detallado (verbose)",
            variable=self.verbose_var
        )
        self.verbose_check.pack(anchor='w')

        # --- Frame de botones de acción ---
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(0, 10))

        # Botón principal: iniciar análisis (deshabilitado hasta tener archivo).
        self.analyze_btn = ttk.Button(
            action_frame,
            text="🚀 Iniciar Análisis",
            command=self._start_analysis,
            style='Accent.TButton'
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.analyze_btn.config(state='disabled')

        # Botón secundario: limpiar solo los resultados.
        self.clear_results_btn = ttk.Button(
            action_frame,
            text="🧹 Limpiar Resultados",
            command=self._clear_results,
            width=18
        )
        self.clear_results_btn.pack(side=tk.LEFT)

        # Label de estado general (Listo / Analizando / Error).
        self.status_label = tk.Label(
            main_frame,
            text="✅ Listo para analizar",
            font=('Segoe UI', 9),
            fg='#28a745'
        )
        self.status_label.pack(pady=(0, 10))

        # --- Frame de resultados ---
        result_frame = ttk.LabelFrame(main_frame, text="📊 Resultados", padding="15")
        result_frame.pack(fill=tk.BOTH, expand=True)

        # Caja de texto con scroll donde se muestran los resultados.
        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            font=('Consolas', 9),
            bg='#f8f9fa',
            fg='#212529'
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # Frame + barra de progreso (se muestra solo durante el análisis).
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='indeterminate',
            length=100
        )
        self.progress_bar.pack(fill=tk.X)

    def _center_window(self):
        """Centra la ventana en la pantalla."""
        self.root.update_idletasks()                       # Forzar cálculo de tamaño
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def _select_file(self):
        """Abre el selector de archivos nativo de Windows."""
        # Tipos de archivo permitidos en el diálogo.
        file_types = [
            ('Archivos de log', '*.log'),
            ('Archivos de texto', '*.txt'),
            ('Todos los archivos', '*.*')
        ]

        # Abre el diálogo nativo, empezando en Descargas.
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de logs",
            initialdir=str(Path.home() / "Downloads"),
            filetypes=file_types,
            parent=self.root
        )

        # Si el usuario eligió archivo, lo registramos.
        if file_path:
            self._set_file(file_path)

    def _open_downloads(self):
        """Abre directamente la carpeta de Descargas."""
        downloads_path = Path.home() / "Downloads"

        # Fallback al home si no existe Descargas.
        if not downloads_path.exists():
            downloads_path = Path.home()

        file_types = [
            ('Archivos de log', '*.log'),
            ('Archivos de texto', '*.txt'),
            ('Todos los archivos', '*.*')
        ]

        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de logs (Descargas)",
            initialdir=str(downloads_path),
            filetypes=file_types,
            parent=self.root
        )

        if file_path:
            self._set_file(file_path)

    def _open_current_directory(self):
        """Abre la carpeta actual del proyecto."""
        # Directorio padre del paquete (raíz del proyecto).
        current_dir = Path(__file__).parent.parent

        # Fallback al home si por alguna razón no existe.
        if not current_dir.exists():
            current_dir = Path.home()

        file_types = [
            ('Archivos de log', '*.log'),
            ('Archivos de texto', '*.txt'),
            ('Todos los archivos', '*.*')
        ]

        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de logs (Directorio actual)",
            initialdir=str(current_dir),
            filetypes=file_types,
            parent=self.root
        )

        if file_path:
            self._set_file(file_path)

    def _set_file(self, file_path: str):
        """Establece el archivo seleccionado."""
        path = Path(file_path)

        # Validar existencia; si no existe, avisar y salir.
        if not path.exists():
            messagebox.showerror("Error", f"El archivo no existe:\n{file_path}")
            return

        # Guardar la ruta y reflejarla en el entry.
        self.selected_file = file_path
        self.file_path_var.set(file_path)

        # Mostrar nombre y tamaño formateado.
        size = path.stat().st_size
        size_str = self._format_size(size)

        status_text = f"✅ Archivo seleccionado: {path.name} ({size_str})"
        self.file_status.config(text=status_text, fg='#28a745')

        # Habilitar botón de análisis.
        self.analyze_btn.config(state='normal')

        # Limpiar resultados anteriores.
        self._clear_results()

        logger.info(f"Archivo seleccionado: {file_path}")

    def _format_size(self, size: int) -> str:
        """Formatea el tamaño del archivo."""
        # Itera unidades hasta encontrar la adecuada.
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def _clear_all(self):
        """Limpia todo: campo de texto, selección y resultados."""
        # Limpiar el entry de ruta.
        self.file_path_var.set("")

        # Limpiar la selección interna.
        self.selected_file = None

        # Deshabilitar análisis hasta elegir archivo nuevo.
        self.analyze_btn.config(state='disabled')

        # Resetear el label de estado del archivo.
        self.file_status.config(
            text="ℹ️ Selecciona un archivo .log para analizar",
            fg='#666666'
        )

        # Limpiar el área de resultados.
        self._clear_results()

        # Resetear estado general.
        self.status_label.config(text="✅ Listo para analizar", fg='#28a745')

        # Ocultar y detener la barra de progreso si estaba visible.
        self.progress_frame.pack_forget()
        self.progress_bar.stop()

        logger.info("🧹 Todo limpiado")

        # Mensaje de confirmación en el área de resultados.
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "🧹 Todo ha sido limpiado\n\n")
        self.result_text.insert(tk.END, "Selecciona un nuevo archivo para analizar.")

    def _clear_results(self):
        """Limpia solo los resultados del análisis."""
        # Resetear el área de texto con mensaje por defecto.
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "📊 Esperando análisis...\n\n")
        self.result_text.insert(tk.END, "Selecciona un archivo y haz clic en 'Iniciar Análisis'")

        # Si no hay archivo seleccionado, deshabilitar análisis.
        if not self.selected_file:
            self.analyze_btn.config(state='disabled')

    def _start_analysis(self):
        """Inicia el análisis en un hilo separado."""
        # Sin archivo seleccionado no se puede analizar.
        if not self.selected_file:
            messagebox.showwarning("Advertencia", "Por favor, selecciona un archivo primero.")
            return

        # Verificar que el archivo siga existiendo.
        path = Path(self.selected_file)
        if not path.exists():
            messagebox.showerror("Error", "El archivo ya no existe.")
            self._clear_all()
            return

        # Deshabilitar todos los botones mientras corre el análisis.
        self.analyze_btn.config(state='disabled')
        self.select_btn.config(state='disabled')
        self.downloads_btn.config(state='disabled')
        self.current_dir_btn.config(state='disabled')
        self.clear_btn.config(state='disabled')
        self.clear_results_btn.config(state='disabled')

        # Mostrar y arrancar la barra de progreso.
        self.progress_frame.pack(fill=tk.X, pady=(10, 0))
        self.progress_bar.start()

        # Actualizar estado visual.
        self.status_label.config(text="⏳ Analizando...", fg='#ffc107')
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "⏳ Procesando archivo...\n\n")
        self.result_text.see(tk.END)

        # Lanzar el análisis en un hilo daemon para no bloquear la GUI.
        self.analysis_thread = threading.Thread(
            target=self._run_analysis,
            daemon=True
        )
        self.analysis_thread.start()

        # Empezar a chequear progreso periódicamente.
        self._check_analysis_progress()

    def _run_analysis(self):
        """Ejecuta el análisis (en hilo separado)."""
        try:
            # Actualizar el estado desde el hilo principal (thread-safe).
            self.root.after(0, lambda: self.status_label.config(
                text="🔄 Procesando logs...",
                fg='#17a2b8'
            ))

            # Import diferido para no cargar servicios si no se usan.
            from ..services.analysis_service import AnalysisService
            from ..config import Config

            # Crear el servicio si aún no existe (lazy).
            if self.service is None:
                self.service = AnalysisService(Config())

            # Ejecutar el análisis sobre el archivo seleccionado.
            result = self.service.analyze_file(self.selected_file)

            # Mostrar resultados en el hilo principal.
            self.root.after(0, lambda: self._show_results(result))

        except Exception as err:
            # Loguear y mostrar error al usuario.
            logger.error(f"Error en análisis: {str(err)}", exc_info=True)
            error_msg = str(err)
            self.root.after(0, lambda: self._show_error(error_msg))

    def _check_analysis_progress(self):
        """Verifica el progreso del análisis."""
        # Mientras el hilo siga vivo, animar el estado.
        if self.analysis_thread and self.analysis_thread.is_alive():
            self._progress_count += 1
            dots = '.' * (self._progress_count % 4)
            self.root.after(0, lambda: self.status_label.config(
                text=f"⏳ Procesando{dots}",
                fg='#17a2b8'
            ))

            # Volver a chequear en 500 ms.
            self.root.after(500, self._check_analysis_progress)

    def _show_results(self, result: dict):
        """Muestra los resultados del análisis."""
        # Detener y ocultar la barra de progreso.
        self.progress_bar.stop()
        self.progress_frame.pack_forget()

        # Rehabilitar botones.
        self.analyze_btn.config(state='normal')
        self.select_btn.config(state='normal')
        self.downloads_btn.config(state='normal')
        self.current_dir_btn.config(state='normal')
        self.clear_btn.config(state='normal')
        self.clear_results_btn.config(state='normal')

        # Estado general OK.
        self.status_label.config(text="✅ Análisis completado", fg='#28a745')

        # Construir el texto de salida.
        output = []
        output.append("=" * 70)
        output.append("📊 RESULTADOS DEL ANÁLISIS")
        output.append("=" * 70)
        output.append("")

        # Si el servicio devolvió un error, mostrarlo y salir.
        if 'error' in result:
            output.append(f"❌ Error: {result['error']}")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "\n".join(output))
            return

        # Resumen básico.
        output.append(f"📁 Archivo: {result.get('file', 'N/A')}")
        output.append(f"📊 Total de logs: {result.get('total_logs', 0):,}")
        output.append(f"🔄 Transacciones: {result.get('total_groups', 0):,}")
        output.append(f"⚠️ Errores detectados: {len(result.get('errors', []))}")
        output.append("")

        # Bloque de análisis con IA.
        ai_analysis = result.get('ai_analysis', {})
        output.append("🤖 ANÁLISIS CON IA")
        output.append("-" * 70)
        output.append(f"Estado: {ai_analysis.get('status', 'No disponible')}")

        if ai_analysis.get('status') == 'success':
            analysis_text = ai_analysis.get('analysis', '')
            if analysis_text:
                output.append("")
                output.append("📝 Recomendaciones:")
                output.append(analysis_text[:500])           # Primeros 500 chars
                if len(analysis_text) > 500:
                    output.append("... (análisis completo disponible en el reporte)")
        elif ai_analysis.get('status') == 'offline':
            output.append("⚠️ Análisis IA no disponible - usando modo offline")
        else:
            output.append(f"⚠️ {ai_analysis.get('analysis', 'Error en análisis IA')}")

        output.append("")

        # Bloque de errores (top 10).
        errors = result.get('errors', [])
        if errors:
            output.append("⚠️ ERRORES ENCONTRADOS")
            output.append("-" * 70)

            for i, error in enumerate(errors[:10], 1):
                output.append(f"\n{i}. Correlation ID: {error.get('correlation_id', 'N/A')}")
                output.append(f"   Errores: {error.get('error_count', 0)}")
                if error.get('messages'):
                    first_msg = error.get('messages', [''])[0]
                    # Truncar mensaje largo para no romper el layout.
                    if len(first_msg) > 100:
                        first_msg = first_msg[:100] + "..."
                    output.append(f"   Primer error: {first_msg}")

            if len(errors) > 10:
                output.append(f"\n... y {len(errors) - 10} errores más")
        else:
            output.append("✅ No se encontraron errores")

        output.append("")
        output.append("=" * 70)

        # Ruta del reporte generado, si existe.
        report_path = result.get('report_path')
        if report_path:
            output.append(f"📄 Reporte guardado en: {report_path}")

        output.append("=" * 70)

        # Volcar todo al widget de texto.
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "\n".join(output))
        self.result_text.see(tk.END)

    def _show_error(self, error_msg: str):
        """Muestra un error en la interfaz."""
        # Detener y ocultar la barra de progreso.
        self.progress_bar.stop()
        self.progress_frame.pack_forget()

        # Rehabilitar botones.
        self.analyze_btn.config(state='normal')
        self.select_btn.config(state='normal')
        self.downloads_btn.config(state='normal')
        self.current_dir_btn.config(state='normal')
        self.clear_btn.config(state='normal')
        self.clear_results_btn.config(state='normal')

        # Estado visual de error.
        self.status_label.config(text="❌ Error en el análisis", fg='#dc3545')

        # Mostrar detalles del error en el área de resultados.
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "❌ ERROR EN EL ANÁLISIS\n")
        self.result_text.insert(tk.END, "=" * 50 + "\n\n")
        self.result_text.insert(tk.END, f"Error: {error_msg}\n\n")
        self.result_text.insert(tk.END, "Revisa los logs para más detalles.\n\n")
        self.result_text.insert(tk.END, "💡 Sugerencia: Limpia la selección y prueba con otro archivo.")

        # Diálogo modal de error.
        messagebox.showerror("Error de Análisis", f"Ocurrió un error:\n\n{error_msg}")