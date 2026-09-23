; Log Analyzer - Instalador Inno Setup
; Compilar con: iscc installer.iss
; Requiere: Inno Setup 6+ (https://jrsoftware.org/isinfo.php)

#define MyAppName "Log Analyzer IA"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Log Analyzer Team"
#define MyAppURL "https://github.com/tu-usuario/log-analyzer"
#define MyAppExeName "LogAnalyzer.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist_installer
OutputBaseFilename=LogAnalyzer_Setup_v{#MyAppVersion}
SetupIconFile=assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "installollama"; Description: "Instalar Ollama (IA local)"; GroupDescription: "Dependencias:"; Flags: checked
Name: "installgraphviz"; Description: "Instalar Graphviz (diagramas PNG)"; GroupDescription: "Dependencias:"; Flags: checked

[Files]
Source: "dist\LogAnalyzer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "scripts\install_deps.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "README_USUARIO.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Instalar Ollama silenciosamente
Filename: "cmd.exe"; Parameters: "/c winget install Ollama.Ollama --silent --accept-source-agreements --accept-package-agreements"; StatusMsg: "Instalando Ollama (motor IA)..."; Tasks: installollama; Flags: runhidden waituntilterminated

; Descargar modelo IA
Filename: "cmd.exe"; Parameters: "/c ollama pull qwen2.5-coder:1.5b"; StatusMsg: "Descargando modelo IA (qwen2.5-coder:1.5b)..."; Tasks: installollama; Flags: runhidden waituntilterminated

; Instalar Graphviz
Filename: "cmd.exe"; Parameters: "/c winget install Graphviz.Graphviz --silent --accept-source-agreements --accept-package-agreements"; StatusMsg: "Instalando Graphviz (diagramas)..."; Tasks: installgraphviz; Flags: runhidden waituntilterminated

; Lanzar aplicación al finalizar
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
begin
  // Verificar Windows 10+
  if not CheckWin32Version(10, 0) then begin
    MsgBox('Se requiere Windows 10 o superior.', mbError, MB_OK);
    Result := False;
  end else
    Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    // Asegurar que la carpeta output/reports existe
    ForceDirectories(ExpandConstant('{app}\output\reports'));
    ForceDirectories(ExpandConstant('{app}\logs'));
  end;
end;