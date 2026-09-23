"""
Ventana principal de la interfaz gráfica - Diseño Moderno.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
import logging

logger = logging.getLogger(__name__)


# Paleta de colores moderna
class Colors:
    # Modo claro
    LIGHT = {
        'bg': '#f8f9fa',
        'surface': '#ffffff',
        'surface_hover': '#f1f3f4',
        'primary': '#1a73e8',
        'primary_hover': '#1557b0',
        'primary_light': '#e8f0fe',
        'secondary': '#5f6368',
        'secondary_hover': '#3c4043',
        'success': '#1e8e3e',
        'warning': '#f9ab00',
        'danger': '#d93025',
        'text_primary': '#202124',
        'text_secondary': '#5f6368',
        'text_disabled': '#9aa0a6',
        'border': '#dadce0',
        'border_focus': '#1a73e8',
        'shadow': 'rgba(0,0,0,0.1)',
    }
    # Modo oscuro
    DARK = {
        'bg': '#1e1e1e',
        'surface': '#2d2d2d',
        'surface_hover': '#3c3c3c',
        'primary': '#8ab4f8',
        'primary_hover': '#aecbfa',
        'primary_light': '#1a3a5c',
        'secondary': '#9aa0a6',
        'secondary_hover': '#bdc1c6',
        'success': '#81c995',
        'warning': '#fdd663',
        'danger': '#f28b82',
        'text_primary': '#e8eaed',
        'text_secondary': '#9aa0a6',
        'text_disabled': '#6b6b6b',
        'border': '#3c3c3c',
        'border_focus': '#8ab4f8',
        'shadow': 'rgba(0,0,0,0.3)',
    }


class ModernStyle:
    """Configuración de estilos modernos para ttk."""

    @staticmethod
    def setup(root, dark_mode=False):
        style = ttk.Style(root)
        colors = Colors.DARK if dark_mode else Colors.LIGHT

        # Configurar tema base
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass

        # Variables de color para uso dinámico
        root.colors = colors

        # Estilos base
        style.configure('.', font=('Segoe UI', 10))

        # Frame principal
        style.configure('Main.TFrame', background=colors['bg'])
        style.configure('Card.TFrame', background=colors['surface'], relief='flat', borderwidth=0)

        # Labels
        style.configure('Title.TLabel',
                        font=('Segoe UI', 22, 'bold'),
                        background=colors['bg'],
                        foreground=colors['primary'])
        style.configure('Subtitle.TLabel',
                        font=('Segoe UI', 11),
                        background=colors['bg'],
                        foreground=colors['text_secondary'])
        style.configure('CardTitle.TLabel',
                        font=('Segoe UI', 12, 'bold'),
                        background=colors['surface'],
                        foreground=colors['text_primary'])
        style.configure('Body.TLabel',
                        font=('Segoe UI', 10),
                        background=colors['surface'],
                        foreground=colors['text_primary'])
        style.configure('Secondary.TLabel',
                        font=('Segoe UI', 9),
                        background=colors['surface'],
                        foreground=colors['text_secondary'])
        style.configure('Status.TLabel',
                        font=('Segoe UI', 10, 'bold'),
                        background=colors['bg'],
                        foreground=colors['text_secondary'])
        style.configure('FileStatus.TLabel',
                        font=('Segoe UI', 10),
                        background=colors['bg'],
                        foreground=colors['text_secondary'])

        # Entry
        style.configure('Modern.TEntry',
                        fieldbackground=colors['surface'],
                        foreground=colors['text_primary'],
                        borderwidth=1,
                        relief='solid',
                        padding=8)
        style.map('Modern.TEntry',
                  bordercolor=[('focus', colors['border_focus']),
                               ('!focus', colors['border'])])

        # Buttons
        style.configure('Primary.TButton',
                        font=('Segoe UI', 10, 'bold'),
                        foreground='white',
                        background=colors['primary'],
                        borderwidth=0,
                        padding=(20, 10),
                        focuscolor='none')
        style.map('Primary.TButton',
                  background=[('active', colors['primary_hover']),
                              ('disabled', colors['text_disabled'])])

        style.configure('Secondary.TButton',
                        font=('Segoe UI', 10),
                        foreground=colors['text_primary'],
                        background=colors['surface'],
                        borderwidth=1,
                        relief='solid',
                        padding=(16, 10),
                        focuscolor='none')
        style.map('Secondary.TButton',
                  background=[('active', colors['surface_hover']),
                              ('disabled', colors['surface'])],
                  foreground=[('disabled', colors['text_disabled'])])

        style.configure('Ghost.TButton',
                        font=('Segoe UI', 10),
                        foreground=colors['primary'],
                        background=colors['primary_light'],
                        borderwidth=0,
                        padding=(16, 10),
                        focuscolor='none')
        style.map('Ghost.TButton',
                  background=[('active', '#d2e3fc'),
                              ('disabled', colors['primary_light'])],
                  foreground=[('disabled', colors['text_disabled'])])

        style.configure('Danger.TButton',
                        font=('Segoe UI', 10),
                        foreground='white',
                        background=colors['danger'],
                        borderwidth=0,
                        padding=(16, 10),
                        focuscolor='none')
        style.map('Danger.TButton',
                  background=[('active', '#c5221f'),
                              ('disabled', colors['text_disabled'])])

        # Checkbutton
        style.configure('Modern.TCheckbutton',
                        font=('Segoe UI', 10),
                        background=colors['surface'],
                        foreground=colors['text_primary'],
                        focuscolor=colors['primary'])
        style.map('Modern.TCheckbutton',
                  background=[('active', colors['surface_hover'])])

        # Labelframe
        style.configure('Card.TLabelframe',
                        background=colors['surface'],
                        borderwidth=0,
                        relief='flat')
        style.configure('Card.TLabelframe.Label',
                        font=('Segoe UI', 11, 'bold'),
                        background=colors['surface'],
                        foreground=colors['text_primary'])

        # Progressbar
        style.configure('Modern.Horizontal.TProgressbar',
                        troughcolor=colors['border'],
                        background=colors['primary'],
                        borderwidth=0,
                        lightcolor=colors['primary'],
                        darkcolor=colors['primary'])

        # Separator
        style.configure('Modern.TSeparator', background=colors['border'])

        return colors


class MainWindow:
    """Ventana principal de la aplicación con diseño moderno."""

    def __init__(self):
        self.root = None
        self.selected_file = None
        self.analysis_thread = None
        self.service = None
        self._progress_count = 0
        self.dark_mode = False  # Por defecto modo claro
        self.colors = Colors.LIGHT

    def run(self):
        """Ejecuta la interfaz gráfica."""
        self.root = tk.Tk()
        self.root.title("Analizador de Logs con IA")
        self.root.geometry("1000x750")
        self.root.minsize(900, 650)

        # Configurar estilos modernos
        self.colors = ModernStyle.setup(self.root, self.dark_mode)
        self.root.configure(bg=self.colors['bg'])

        # Configurar icono de ventana (opcional)
        self._setup_window()

        self._create_widgets()
        self._center_window()
        self.root.mainloop()

    def _setup_window(self):
        """Configuración adicional de la ventana."""
        # Hacer que la ventana se vea más moderna en Windows
        try:
            self.root.attributes('-alpha', 1.0)
        except tk.TclError:
            pass

    def _create_widgets(self):
        """Crea todos los widgets de la interfaz con diseño moderno."""
        # Contenedor principal con scroll si es necesario
        main_container = ttk.Frame(self.root, style='Main.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

        # Header
        self._create_header(main_container)

        # Área de contenido con grid para mejor control
        content = ttk.Frame(main_container, style='Main.TFrame')
        content.pack(fill=tk.BOTH, expand=True, pady=(16, 0))
        content.columnconfigure(0, weight=1)

        # Sección: Archivo
        self._create_file_section(content)

        # Sección: Configuración
        self._create_config_section(content)

        # Sección: Acciones
        self._create_action_section(content)

        # Sección: Resultados
        self._create_results_section(content)

        # Barra de progreso (inicialmente oculta)
        self._create_progress_bar(main_container)

    def _create_header(self, parent):
        """Crea el encabezado moderno."""
        header = ttk.Frame(parent, style='Main.TFrame')
        header.pack(fill=tk.X, pady=(0, 8))

        # Título principal
        self.title_label = ttk.Label(
            header,
            text="📊 Analizador de Logs con IA",
            style='Title.TLabel'
        )
        self.title_label.pack(anchor='w')

        # Subtítulo
        self.subtitle_label = ttk.Label(
            header,
            text="Analiza, correlaciona y diagnostica errores en tus logs automáticamente",
            style='Subtitle.TLabel'
        )
        self.subtitle_label.pack(anchor='w', pady=(4, 0))

        # Separador visual
        sep = ttk.Separator(header, orient='horizontal', style='Modern.TSeparator')
        sep.pack(fill=tk.X, pady=(16, 0))

    def _create_file_section(self, parent):
        """Crea la sección de selección de archivo."""
        card = ttk.LabelFrame(parent, text="📁  Archivo de Logs", style='Card.TLabelframe', padding=20)
        card.grid(row=0, column=0, sticky='ew', pady=(0, 16))
        card.columnconfigure(0, weight=1)

        # Entry + botón limpiar en fila
        entry_row = ttk.Frame(card, style='Card.TFrame')
        entry_row.grid(row=0, column=0, sticky='ew', pady=(0, 12))
        entry_row.columnconfigure(0, weight=1)

        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(
            entry_row,
            textvariable=self.file_path_var,
            style='Modern.TEntry',
            state='readonly'
        )
        self.file_entry.grid(row=0, column=0, sticky='ew', padx=(0, 12))

        self.clear_btn = ttk.Button(
            entry_row,
            text="🗑️ Limpiar",
            command=self._clear_all,
            style='Secondary.TButton'
        )
        self.clear_btn.grid(row=0, column=1)

        # Botones de navegación
        nav_frame = ttk.Frame(card, style='Card.TFrame')
        nav_frame.grid(row=1, column=0, sticky='ew')

        self.select_btn = ttk.Button(
            nav_frame,
            text="📂 Examinar...",
            command=self._select_file,
            style='Primary.TButton'
        )
        self.select_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.downloads_btn = ttk.Button(
            nav_frame,
            text="📥 Descargas",
            command=self._open_downloads,
            style='Ghost.TButton'
        )
        self.downloads_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.current_dir_btn = ttk.Button(
            nav_frame,
            text="📂 Carpeta actual",
            command=self._open_current_directory,
            style='Ghost.TButton'
        )
        self.current_dir_btn.pack(side=tk.LEFT)

        # Status del archivo
        self.file_status = ttk.Label(
            card,
            text="ℹ️ Selecciona un archivo .log o .txt para analizar",
            style='FileStatus.TLabel'
        )
        self.file_status.grid(row=2, column=0, sticky='w', pady=(12, 0))

    def _create_config_section(self, parent):
        """Crea la sección de configuración."""
        card = ttk.LabelFrame(parent, text="⚙️  Configuración", style='Card.TLabelframe', padding=20)
        card.grid(row=1, column=0, sticky='ew', pady=(0, 16))

        # Grid de checkboxes
        checks_frame = ttk.Frame(card, style='Card.TFrame')
        checks_frame.pack(fill=tk.X)

        self.use_ai_var = tk.BooleanVar(value=True)
        self.use_ai_check = ttk.Checkbutton(
            checks_frame,
            text="Usar IA para análisis (Ollama local)",
            variable=self.use_ai_var,
            style='Modern.TCheckbutton'
        )
        self.use_ai_check.pack(anchor='w', pady=4)

        self.verbose_var = tk.BooleanVar(value=False)
        self.verbose_check = ttk.Checkbutton(
            checks_frame,
            text="Modo detallado (verbose logging)",
            variable=self.verbose_var,
            style='Modern.TCheckbutton'
        )
        self.verbose_check.pack(anchor='w', pady=4)

        # Toggle modo oscuro (nuevo)
        self.dark_mode_var = tk.BooleanVar(value=False)
        self.dark_mode_check = ttk.Checkbutton(
            checks_frame,
            text="🌙 Modo oscuro",
            variable=self.dark_mode_var,
            command=self._toggle_dark_mode,
            style='Modern.TCheckbutton'
        )
        self.dark_mode_check.pack(anchor='w', pady=4)

    def _create_action_section(self, parent):
        """Crea la sección de botones de acción."""
        card = ttk.Frame(parent, style='Main.TFrame')
        card.grid(row=2, column=0, sticky='ew', pady=(0, 16))

        # Botón principal
        self.analyze_btn = ttk.Button(
            card,
            text="🚀  Iniciar Análisis",
            command=self._start_analysis,
            style='Primary.TButton',
            state='disabled'
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 12))

        # Botón secundario
        self.clear_results_btn = ttk.Button(
            card,
            text="🧹 Limpiar Resultados",
            command=self._clear_results,
            style='Secondary.TButton'
        )
        self.clear_results_btn.pack(side=tk.LEFT)

        # Status label a la derecha
        self.status_label = ttk.Label(
            card,
            text="✅ Listo para analizar",
            style='Status.TLabel'
        )
        self.status_label.pack(side=tk.RIGHT)

    def _create_results_section(self, parent):
        """Crea la sección de resultados."""
        card = ttk.LabelFrame(parent, text="📊  Resultados del Análisis", style='Card.TLabelframe', padding=16)
        card.grid(row=3, column=0, sticky='nsew', pady=(0, 8))
        parent.rowconfigure(3, weight=1)
        card.rowconfigure(0, weight=1)
        card.columnconfigure(0, weight=1)

        # Toolbar de resultados
        toolbar = ttk.Frame(card, style='Card.TFrame')
        toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 8))

        ttk.Label(toolbar, text="Salida del análisis", style='CardTitle.TLabel').pack(side=tk.LEFT)

        # Botones de acción en resultados
        ttk.Button(toolbar, text="📋 Copiar", command=self._copy_results, style='Ghost.TButton').pack(side=tk.RIGHT, padx=4)
        ttk.Button(toolbar, text="💾 Guardar", command=self._save_results, style='Ghost.TButton').pack(side=tk.RIGHT, padx=4)
        ttk.Button(toolbar, text="📄 Abrir Reporte", command=self._open_report, style='Ghost.TButton').pack(side=tk.RIGHT, padx=4)

        # Área de texto con mejor estilo
        self.result_text = scrolledtext.ScrolledText(
            card,
            wrap=tk.WORD,
            font=('JetBrains Mono', 10) if self._font_exists('JetBrains Mono') else ('Consolas', 10),
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['primary'],
            selectbackground=self.colors['primary_light'],
            selectforeground=self.colors['text_primary'],
            borderwidth=1,
            relief='solid',
            highlightthickness=1,
            highlightcolor=self.colors['border_focus'],
            highlightbackground=self.colors['border'],
            padx=12,
            pady=12
        )
        self.result_text.grid(row=1, column=0, sticky='nsew')

        # Configurar tags para colores en el texto
        self._configure_text_tags()

        # Mensaje inicial
        self._set_initial_message()

    def _create_progress_bar(self, parent):
        """Crea la barra de progreso moderna."""
        self.progress_frame = ttk.Frame(parent, style='Main.TFrame')
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='indeterminate',
            style='Modern.Horizontal.TProgressbar',
            length=300
        )
        self.progress_bar.pack(fill=tk.X, pady=(8, 0))

        # Label de progreso
        self.progress_label = ttk.Label(
            self.progress_frame,
            text="",
            style='Secondary.TLabel'
        )
        self.progress_label.pack(anchor='w', pady=(4, 0))

    def _configure_text_tags(self):
        """Configura tags de color para el área de resultados."""
        tags = {
            'title': {'font': ('Segoe UI', 11, 'bold'), 'foreground': self.colors['primary']},
            'subtitle': {'font': ('Segoe UI', 10, 'bold'), 'foreground': self.colors['text_primary']},
            'success': {'foreground': self.colors['success']},
            'warning': {'foreground': self.colors['warning']},
            'danger': {'foreground': self.colors['danger']},
            'info': {'foreground': self.colors['primary']},
            'muted': {'foreground': self.colors['text_secondary']},
            'code': {'font': ('JetBrains Mono', 9) if self._font_exists('JetBrains Mono') else ('Consolas', 9),
                     'background': self.colors['bg']},
            'dim': {'foreground': self.colors['text_secondary']},
        }
        for tag, config in tags.items():
            self.result_text.tag_configure(tag, **config)

    def _font_exists(self, font_name):
        """Verifica si una fuente existe en el sistema."""
        try:
            import tkinter.font as tkfont
            return font_name in tkfont.families()
        except:
            return False

    def _set_initial_message(self):
        """Establece el mensaje inicial en el área de resultados."""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "📊 ", 'title')
        self.result_text.insert(tk.END, "Esperando análisis...\n\n", 'muted')
        self.result_text.insert(tk.END, "1. Selecciona un archivo de logs (.log, .txt)\n", 'body')
        self.result_text.insert(tk.END, "2. Configura las opciones si lo deseas\n", 'body')
        self.result_text.insert(tk.END, "3. Haz clic en \"Iniciar Análisis\"\n\n", 'body')
        self.result_text.insert(tk.END, "El analizador procesará el archivo, agrupará por correlation ID,\n", 'dim')
        self.result_text.insert(tk.END, "deduplicará errores repetidos y generará recomendaciones con IA.", 'dim')

    def _center_window(self):
        """Centra la ventana en la pantalla."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def _toggle_dark_mode(self):
        """Alterna entre modo claro y oscuro."""
        self.dark_mode = self.dark_mode_var.get()
        self.colors = ModernStyle.setup(self.root, self.dark_mode)
        self.root.configure(bg=self.colors['bg'])

        # Actualizar widgets principales
        self._refresh_styles()

    def _refresh_styles(self):
        """Refresca los estilos después de cambiar tema."""
        # Actualizar colores de widgets tk (no ttk)
        self.result_text.configure(
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['primary'],
            selectbackground=self.colors['primary_light'],
            highlightcolor=self.colors['border_focus'],
            highlightbackground=self.colors['border']
        )
        self._configure_text_tags()
        self._set_initial_message()

    # --- Métodos de funcionalidad (mantenidos igual) ---

    def _select_file(self):
        file_types = [
            ('Archivos de log', '*.log'),
            ('Archivos de texto', '*.txt'),
            ('Todos los archivos', '*.*')
        ]
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de logs",
            initialdir=str(Path.home() / "Downloads"),
            filetypes=file_types,
            parent=self.root
        )
        if file_path:
            self._set_file(file_path)

    def _open_downloads(self):
        downloads_path = Path.home() / "Downloads"
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
        current_dir = Path(__file__).parent.parent
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
        path = Path(file_path)
        if not path.exists():
            messagebox.showerror("Error", f"El archivo no existe:\n{file_path}")
            return

        self.selected_file = file_path
        self.file_path_var.set(file_path)

        size = path.stat().st_size
        size_str = self._format_size(size)

        status_text = f"✅  {path.name}  •  {size_str}"
        self.file_status.config(text=status_text, foreground=self.colors['success'])

        self.analyze_btn.config(state='normal')
        self._clear_results()

    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def _clear_all(self):
        self.file_path_var.set("")
        self.selected_file = None
        self.analyze_btn.config(state='disabled')
        self.file_status.config(text="ℹ️ Selecciona un archivo .log o .txt para analizar", foreground=self.colors['text_secondary'])
        self._clear_results()
        self.status_label.config(text="✅ Listo para analizar", foreground=self.colors['success'])
        self.progress_frame.pack_forget()
        self.progress_bar.stop()

    def _clear_results(self):
        self.result_text.delete(1.0, tk.END)
        self._set_initial_message()
        if not self.selected_file:
            self.analyze_btn.config(state='disabled')

    def _copy_results(self):
        text = self.result_text.get(1.0, tk.END).strip()
        if text and text != "📊 Esperando análisis...":
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._show_toast("Copiado al portapapeles")
        else:
            self._show_toast("No hay resultados para copiar")

    def _save_results(self):
        text = self.result_text.get(1.0, tk.END).strip()
        if not text or text == "📊 Esperando análisis...":
            self._show_toast("No hay resultados para guardar")
            return

        file_path = filedialog.asksaveasfilename(
            title="Guardar resultados",
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("Markdown", "*.md"), ("Todos", "*.*")],
            parent=self.root
        )
        if file_path:
            try:
                Path(file_path).write_text(text, encoding='utf-8')
                self._show_toast(f"Guardado en {Path(file_path).name}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {e}")

    def _open_report(self):
        # Intentar encontrar el último reporte.
        # Se usa Config().REPORTS_DIR porque en la versión instalada (.exe)
        # __file__ apunta al temporal de PyInstaller y "output/reports"
        # relativo caería en Program Files (solo lectura).
        from ..config import Config
        reports_dir = Config().REPORTS_DIR
        if reports_dir.exists():
            reports = list(reports_dir.glob("*.md"))
            if reports:
                latest = max(reports, key=lambda f: f.stat().st_mtime)
                import subprocess, sys
                try:
                    if sys.platform == 'win32':
                        os.startfile(latest)
                    elif sys.platform == 'darwin':
                        subprocess.run(['open', latest])
                    else:
                        subprocess.run(['xdg-open', latest])
                    self._show_toast("Reporte abierto")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo abrir: {e}")
            else:
                self._show_toast("No hay reportes generados")
        else:
            self._show_toast("Directorio de reportes no encontrado")

    def _show_toast(self, message):
        """Muestra un mensaje toast temporal."""
        # Actualizar status label temporalmente
        original = self.status_label.cget('text')
        self.status_label.config(text=message, foreground=self.colors['primary'])
        self.root.after(3000, lambda: self.status_label.config(text=original, foreground=self.colors['text_secondary']))

    def _start_analysis(self):
        if not self.selected_file:
            messagebox.showwarning("Advertencia", "Por favor, selecciona un archivo primero.")
            return

        path = Path(self.selected_file)
        if not path.exists():
            messagebox.showerror("Error", "El archivo ya no existe.")
            self._clear_all()
            return

        # Deshabilitar botones
        for btn in [self.analyze_btn, self.clear_btn, self.select_btn,
                    self.downloads_btn, self.current_dir_btn, self.clear_results_btn]:
            btn.config(state='disabled')

        # Mostrar progreso
        self.progress_frame.pack(fill=tk.X, pady=(12, 0))
        self.progress_bar.start(10)
        self.progress_label.config(text="Iniciando análisis...")

        self.status_label.config(text="⏳ Analizando...", foreground=self.colors['warning'])
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "⏳ Procesando archivo...\n\n", 'warning')
        self.result_text.see(tk.END)

        self.analysis_thread = threading.Thread(target=self._run_analysis, daemon=True)
        self.analysis_thread.start()
        self._check_analysis_progress()

    def _run_analysis(self):
        try:
            self.root.after(0, lambda: self._update_progress("🔄 Procesando logs...", self.colors['primary']))

            from ..services.analysis_service import AnalysisService
            from ..config import Config

            if self.service is None:
                self.service = AnalysisService(Config())

            result = self.service.analyze_file(self.selected_file)
            self.root.after(0, lambda: self._show_results(result))

        except Exception as err:
            logger.error(f"Error en análisis: {str(err)}", exc_info=True)
            self.root.after(0, lambda: self._show_error(str(err)))

    def _update_progress(self, text, color):
        self.status_label.config(text=text, foreground=color)
        self.progress_label.config(text=text)

    def _check_analysis_progress(self):
        if self.analysis_thread and self.analysis_thread.is_alive():
            self._progress_count += 1
            dots = '.' * (self._progress_count % 4)
            self.root.after(0, lambda: self._update_progress(f"⏳ Procesando{dots}", self.colors['primary']))
            self.root.after(500, self._check_analysis_progress)

    def _show_results(self, result: dict):
        self.progress_bar.stop()
        self.progress_frame.pack_forget()

        for btn in [self.analyze_btn, self.clear_btn, self.select_btn,
                    self.downloads_btn, self.current_dir_btn, self.clear_results_btn]:
            btn.config(state='normal')

        self.status_label.config(text="✅ Análisis completado", foreground=self.colors['success'])

        self.result_text.delete(1.0, tk.END)

        if 'error' in result:
            self.result_text.insert(tk.END, "❌ Error: ", 'danger')
            self.result_text.insert(tk.END, result['error'], 'body')
            return

        # Resumen con estilo
        self.result_text.insert(tk.END, "📊  RESUMEN DEL ANÁLISIS\n", 'title')
        self.result_text.insert(tk.END, "━" * 50 + "\n\n", 'dim')

        self.result_text.insert(tk.END, f"📁 Archivo: ", 'muted')
        self.result_text.insert(tk.END, f"{Path(result.get('file', 'N/A')).name}\n", 'body')

        self.result_text.insert(tk.END, f"📊 Logs totales: ", 'muted')
        self.result_text.insert(tk.END, f"{result.get('total_logs', 0):,}\n", 'body')

        self.result_text.insert(tk.END, f"🔄 Transacciones: ", 'muted')
        self.result_text.insert(tk.END, f"{result.get('total_groups', 0):,}\n", 'body')

        errors = result.get('errors', [])
        self.result_text.insert(tk.END, f"⚠️ Errores detectados: ", 'muted')
        self.result_text.insert(tk.END, f"{len(errors)}", 'danger' if errors else 'success')
        self.result_text.insert(tk.END, "\n\n")

        # Análisis IA
        ai_analysis = result.get('ai_analysis', {})
        self.result_text.insert(tk.END, "🤖  ANÁLISIS CON IA\n", 'title')
        self.result_text.insert(tk.END, "━" * 50 + "\n\n", 'dim')

        status = ai_analysis.get('status', 'unknown')
        if status == 'success':
            self.result_text.insert(tk.END, "Estado: ", 'muted')
            self.result_text.insert(tk.END, "✅ Completado\n\n", 'success')
            analysis_text = ai_analysis.get('analysis', '')
            if analysis_text:
                self.result_text.insert(tk.END, "📝 Recomendaciones:\n", 'subtitle')
                # Mostrar completo con scroll
                self.result_text.insert(tk.END, analysis_text + "\n\n", 'body')
        elif status == 'offline':
            self.result_text.insert(tk.END, "Estado: ", 'muted')
            self.result_text.insert(tk.END, "⚠️ Modo offline (Ollama no disponible)\n\n", 'warning')
        else:
            self.result_text.insert(tk.END, f"Estado: {status}\n", 'muted')
            self.result_text.insert(tk.END, f"{ai_analysis.get('analysis', 'Error')}\n\n", 'danger')

        # Errores detallados
        if errors:
            self.result_text.insert(tk.END, "⚠️  ERRORES DETALLADOS\n", 'title')
            self.result_text.insert(tk.END, "━" * 50 + "\n\n", 'dim')

            for i, error in enumerate(errors[:15], 1):
                corr_id = error.get('correlation_id', 'N/A')
                count = error.get('error_count', 0)
                merged = error.get('merged_from', 1)

                self.result_text.insert(tk.END, f"{i}. ", 'subtitle')
                self.result_text.insert(tk.END, f"{corr_id}", 'code')
                if merged > 1:
                    self.result_text.insert(tk.END, f"  (fusionado de {merged} IDs)", 'info')
                self.result_text.insert(tk.END, f"  •  {count} ocurrencias\n", 'muted')

                if error.get('original_correlation_ids'):
                    ids = error['original_correlation_ids'][:3]
                    self.result_text.insert(tk.END, f"   IDs: {', '.join(ids)}", 'dim')
                    if len(error['original_correlation_ids']) > 3:
                        self.result_text.insert(tk.END, f" +{len(error['original_correlation_ids']) - 3} más", 'dim')
                    self.result_text.insert(tk.END, "\n", 'dim')

                if error.get('messages'):
                    msg = error['messages'][0][:150]
                    self.result_text.insert(tk.END, f"   {msg}", 'code')
                    if len(error['messages'][0]) > 150:
                        self.result_text.insert(tk.END, "...", 'dim')
                    self.result_text.insert(tk.END, "\n", 'dim')

                self.result_text.insert(tk.END, "\n")

            if len(errors) > 15:
                self.result_text.insert(tk.END, f"... y {len(errors) - 15} errores más\n\n", 'dim')
        else:
            self.result_text.insert(tk.END, "✅  No se encontraron errores\n\n", 'success')

        # Reporte
        report_path = result.get('report_path')
        if report_path:
            self.result_text.insert(tk.END, "━" * 50 + "\n", 'dim')
            self.result_text.insert(tk.END, "📄  Reporte generado: ", 'muted')
            self.result_text.insert(tk.END, f"{report_path}\n", 'code')

        self.result_text.see(tk.END)

    def _show_error(self, error_msg: str):
        self.progress_bar.stop()
        self.progress_frame.pack_forget()

        for btn in [self.analyze_btn, self.clear_btn, self.select_btn,
                    self.downloads_btn, self.current_dir_btn, self.clear_results_btn]:
            btn.config(state='normal')

        self.status_label.config(text="❌ Error en el análisis", foreground=self.colors['danger'])

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "❌  ERROR EN EL ANÁLISIS\n", 'danger')
        self.result_text.insert(tk.END, "━" * 50 + "\n\n", 'dim')
        self.result_text.insert(tk.END, f"{error_msg}\n\n", 'body')
        self.result_text.insert(tk.END, "💡 Revisa los logs (logs/analyzer.log) para más detalles.\n", 'dim')
        self.result_text.insert(tk.END, "💡 Sugerencia: Limpia la selección e intenta con otro archivo.", 'dim')

        messagebox.showerror("Error de Análisis", f"Ocurrió un error:\n\n{error_msg}")


# Para compatibilidad hacia atrás
import os