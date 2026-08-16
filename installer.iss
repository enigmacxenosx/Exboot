#define MyAppName "Exboot"
#define MyAppVersion "0.3.6"
#define MyAppPublisher "Enosx Technologies"
#define MyAppExeName "Exboot.exe"

[Setup]
AppId={{A7D9B25A-2EE5-4A5E-9A08-4D46B2F8B7C1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Exboot
DefaultGroupName=Exboot
OutputDir=installer-output
OutputBaseFilename=ExbootSetup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern dark includetitlebar
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=assets\enosx-ai-splash-logo.ico
WizardImageFile=assets\enosx-ai-splash-wizard.png
WizardImageBackColor=$050505
WizardSmallImageFile=assets\enosx-ai-splash-logo.png
WizardSmallImageBackColor=$050505

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Exboot"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Exboot"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Exboot"; Flags: nowait postinstall skipifsilent
