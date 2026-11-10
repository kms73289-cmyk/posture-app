; ====================================================================
;  바른자세 1.6 — Inno Setup 설치 스크립트
;  PyInstaller를 사용하지 않음. 대상 PC에 시스템 Python이 없어도
;  {app}\python\pythonw.exe (이식 런타임)로 실행한다.
;
;  컴파일 전: frontend\dist 빌드, runtime\python 이식 런타임
;    runtime\python\* → {app}\python (pythonw.exe, Lib\site-packages 포함)
;
;  컴파일: ISCC.exe installer.iss
;  출력: installer\바른자세-설치-1.5.exe
;  사용자 데이터 ~/.posture_app 은 복사·삭제하지 않음.
; ====================================================================

#define MyAppName "바른자세"
#define MyAppVersion "1.6"
#define MyAppPublisher "PostureApp"
#define MyAppId "{{A7F3C2E1-9B4D-4E6A-8C1F-2D5E7A9B3C4D}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
; MediaPipe는 경로에 한글이 있으면 모델을 못 읽는 경우가 있어 ASCII 고정
DefaultDirName=C:\Users\Public\PostureApp
UsePreviousAppDir=no
DefaultGroupName={#MyAppName}
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer
OutputBaseFilename=바른자세-설치-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}
SetupLogging=yes
SetupIconFile=baruna-assets\barun_jase.ico
UninstallDisplayIcon={app}\baruna-assets\barun_jase.ico

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕 화면 바로가기"; GroupDescription: "바로가기:"

[Files]
; --- 앱 진입점·분석 모듈 (기능 코드 변경 없음) ---
Source: "barun_jase.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "analyzer.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "data_manager.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "settings_manager.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "baruna-assets\*"; DestDir: "{app}\baruna-assets"; Flags: ignoreversion
Source: "backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc"

; --- React 빌드 결과. FastAPI가 {app}\frontend\dist 를 서빙 ---
Source: "frontend\dist\*"; DestDir: "{app}\frontend\dist"; Flags: ignoreversion recursesubdirs createallsubdirs

; --- 이식 Python 3.10 + site-packages (컴파일 PC에 runtime\python 이 있어야 함) ---
Source: "runtime\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

; --- WebView2: 설치 중에만 사용, 앱 폴더에 남기지 않음. ~/.posture_app 과 무관 ---
Source: "installer\redist\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall
Source: "installer\redist\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\barun_jase.py"""; WorkingDir: "{app}"; IconFilename: "{app}\baruna-assets\barun_jase.ico"; AppUserModelID: "PostureApp.BarunJase"
Name: "{group}\{#MyAppName} 제거"; Filename: "{uninstallexe}"; IconFilename: "{app}\baruna-assets\barun_jase.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\barun_jase.py"""; WorkingDir: "{app}"; IconFilename: "{app}\baruna-assets\barun_jase.ico"; AppUserModelID: "PostureApp.BarunJase"; Tasks: desktopicon

[Run]
; 1) 오프라인 Evergreen Standalone (인터넷 불필요)
Filename: "{tmp}\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"; Parameters: "/silent /install"; StatusMsg: "Microsoft Edge WebView2 Runtime을 설치하는 중..."; Check: NeedsWebView2; Flags: waituntilterminated skipifdoesntexist
; 2) 실패 시 온라인 Bootstrapper (인터넷 필요)
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Microsoft Edge WebView2 Runtime을 다운로드하여 설치하는 중..."; Check: NeedsWebView2; Flags: waituntilterminated skipifdoesntexist
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\barun_jase.py"""; WorkingDir: "{app}"; Description: "바른자세 실행"; Check: IsWebView2Installed; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\backend\__pycache__"
; 측정 기록은 설치 폴더 밖(%USERPROFILE%\.posture_app)에 있으므로 제거하지 않음

[Code]
const
  WebView2Guid = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function WebView2VersionFrom(RootKey: Integer; SubKey: String): String;
begin
  if not RegQueryStringValue(RootKey, SubKey, 'pv', Result) then
    Result := '';
end;

function IsWebView2Installed: Boolean;
var
  Ver: String;
begin
  Ver := WebView2VersionFrom(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\' + WebView2Guid);
  if Ver = '' then
    Ver := WebView2VersionFrom(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + WebView2Guid);
  if Ver = '' then
    Ver := WebView2VersionFrom(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + WebView2Guid);
  Result := (Ver <> '') and (Ver <> '0.0.0.0');
end;

function NeedsWebView2: Boolean;
begin
  Result := not IsWebView2Installed;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not IsWebView2Installed then
    begin
      MsgBox(
        '바른자세 앱 파일은 설치되었지만, Microsoft Edge WebView2 Runtime을 설치하지 못했습니다.' + #13#10#13#10 +
        'WebView2가 없으면 바탕 화면 아이콘을 눌러도 창이 열리지 않습니다.' + #13#10#13#10 +
        '인터넷이 되는 PC에서는 설치 프로그램을 다시 실행해 주세요.' + #13#10 +
        '오프라인 PC라면 설치 파일에 포함된 WebView2 오프라인 설치가 실패했는지,' + #13#10 +
        '관리자 권한으로 다시 설치해 보세요.' + #13#10#13#10 +
        '측정 기록(%USERPROFILE%\.posture_app)은 변경하지 않았습니다.',
        mbCriticalError,
        MB_OK
      );
    end;
  end;
end;
