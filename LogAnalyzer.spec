# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/Users/pc/Desktop/log-analyzer-app/main_entry.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/Users/pc/Desktop/log-analyzer-app/app', 'app')],
    hiddenimports=['yaml', 'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.scrolledtext', 'requests', 'colorama', 'dotenv', 'dataclasses_json', 'typing_extensions', 'app.config', 'app.core.log_parser', 'app.core.correlation_analyzer', 'app.core.smart_filter', 'app.core.log_splitter', 'app.services.analysis_service', 'app.services.ai_analyzer', 'app.ai.ollama_client', 'app.ai.prompt_builder', 'app.reporters.markdown_reporter', 'app.utils.file_utils', 'app.utils.ollama_checker', 'app.models.log_entry', 'app.models.correlation_group', 'app.models.error_report', 'app.gui.main_window'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LogAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE',
)
