; Inno Setup builds the SINGLE distributable AcapellaDownloaderSetup.exe.
#define AppVersion GetEnv("ACAPELLA_VERSION")
[Setup]
AppId={{C43E0DD7-59E2-475C-B4BB-1E667F3E1B6A}
AppName=Acapella Downloader
AppVersion={#AppVersion}
AppPublisher=Jakari
DefaultDirName={localappdata}\Programs\AcapellaDownloader
DefaultGroupName=Acapella Downloader
PrivilegesRequired=lowest
OutputDir=release
OutputBaseFilename=AcapellaDownloaderSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\AcapellaDownloader.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Files]
Source: "dist\AcapellaDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Acapella Downloader"; Filename: "{app}\AcapellaDownloader.exe"
Name: "{autodesktop}\Acapella Downloader"; Filename: "{app}\AcapellaDownloader.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: checkedonce

[Run]
Filename: "{app}\AcapellaDownloader.exe"; Description: "Launch Acapella Downloader"; Flags: nowait postinstall skipifsilent
