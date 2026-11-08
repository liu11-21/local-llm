#define AppName "Local LLM"
#define AppExe "LocalLLM.exe"
#define ProjectUrl "https://github.com/liu11-21/local-llm"

[Setup]
AppId={{D03B7A5E-CC74-472E-B620-A978A505B6C1}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Local LLM Project
AppPublisherURL={#ProjectUrl}
AppSupportURL={#ProjectUrl}/issues
AppUpdatesURL={#ProjectUrl}/releases/latest
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=logo.ico
OutputBaseFilename=LocalLLM-v{#AppVersion}-Windows-x64-Setup
VersionInfoVersion={#AppVersion}.0
VersionInfoDescription=Local LLM Windows Installer
CloseApplications=yes
RestartApplications=no
#ifdef Signed
SignTool=release
SignedUninstaller=yes
#endif

[Languages]
#if FileExists(CompilerPath + "Languages\ChineseTraditional.isl")
Name: "cht"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"
#endif
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
