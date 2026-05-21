; RemoteEye v3.0 - Inno Setup 安装脚本 (Windows 11)
; 使用方法: iscc.exe RemoteEye.iss

#define MyAppName "RemoteEye"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "RemoteEye Team"
#define MyAppURL "https://github.com/kaising/RemoteEye"

[Setup]
AppId={{A7F2E8B1-4C3D-4E9A-B5F6-123456789ABC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\..\LICENSE
OutputDir=Output
OutputBaseFilename=RemoteEye-v3.0-x64
SetupIconFile=remoteeye.ico
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinese"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "chinesetraditional"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart_agent"; Description: "开机自动启动被控端"; GroupDescription: "开机启动:";
Name: "autostart_server"; Description: "开机自动启动信令服务器"; GroupDescription: "开机启动:";
Name: "firewall_exception"; Description: "添加防火墙例外"; GroupDescription: "网络设置:";

[Files]
Source: "..\..\dist\RemoteEyeAgent.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\RemoteEyeServer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\RemoteEye 被控端"; Filename: "{app}\RemoteEyeAgent.exe"
Name: "{group}\RemoteEye 信令服务器"; Filename: "{app}\RemoteEyeServer.exe"
Name: "{group}\{cm:UninstallProgram,RemoteEye}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\RemoteEye 被控端"; Filename: "{app}\RemoteEyeAgent.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RemoteEyeAgent.exe"; Description: "启动被控端"; Flags: nowait postinstall skipifsilent
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""RemoteEye"" dir=in action=allow program=""{app}\RemoteEyeAgent.exe"" enable=yes"; Tasks: firewall_exception; Flags: runhidden

[Registry]
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "RemoteEyeAgent"; ValueData: """{app}\RemoteEyeAgent.exe"" --server ws://localhost:8000/ws/agent"; Tasks: autostart_agent; Flags: uninsdeletevalue
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "RemoteEyeServer"; ValueData: """{app}\RemoteEyeServer.exe"""; Tasks: autostart_server; Flags: uninsdeletevalue

[UninstallDelete]
Type: filesandordirs; Name: "{app}\config.json"
Type: filesandordirs; Name: "{%USERPROFILE}\.remoteeye"
