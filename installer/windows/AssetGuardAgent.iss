; AssetGuard Agent bootstrapper for Windows x64.
; Build with: scripts\windows\build-agent-installer.ps1
; The wizard installs the official GLPI Agent through WinGet and configures only the
; AssetGuard-owned privacy-limited profile. It does not package or modify GLPI Agent.

#define AppName "AssetGuard Agent"
#define AppVersion "0.1.8"
#define AppPublisher "AssetGuard"
#define AppGuid "{{7BF917A0-D474-45CA-89E5-2F19C83142B3}"

[Setup]
AppId={#AppGuid}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\AssetGuard Agent
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\installer-output
OutputBaseFilename=AssetGuard-Agent-Setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}
SetupLogging=no

[Files]
Source: "..\..\scripts\windows\install-assetguard-agent-service.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\scripts\windows\install-assetguard-agent-from-config.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\scripts\windows\request-assetguard-agent-reenrolment.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\scripts\windows\uninstall-assetguard-agent-service.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\scripts\windows\test-assetguard-agent-readiness.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\scripts\windows\assetguard-agent-runtime.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\scripts\windows\run-assetguard-agent.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\scripts\windows\update-assetguard-agent.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\scripts\windows\glpi-agent-minimal-profile.cfg"; DestDir: "{app}"; Flags: ignoreversion

[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\uninstall-assetguard-agent-service.ps1"""; Flags: runhidden waituntilterminated; RunOnceId: "AssetGuardAgentRemoveConfiguration"

[Code]
var
  GatewayPage: TInputQueryWizardPage;
  EnrollmentPage: TInputOptionWizardPage;
  CredentialPage: TInputQueryWizardPage;
  OptionsPage: TInputOptionWizardPage;
  OneTimeConfigPath: String;

function IsValidUsername(Value: String): Boolean;
var
  I: Integer;
  Character: Char;
begin
  Result := (Length(Value) >= 3) and (Length(Value) <= 128);
  if not Result then Exit;
  for I := 1 to Length(Value) do begin
    Character := Value[I];
    if not (((Character >= 'A') and (Character <= 'Z')) or
            ((Character >= 'a') and (Character <= 'z')) or
            ((Character >= '0') and (Character <= '9')) or (Character = '-')) then begin
      Result := False;
      Exit;
    end;
  end;
end;

function IsValidGateway(Value: String): Boolean;
var
  Lower: String;
begin
  Lower := Lowercase(Value);
  Result := (Pos('https://', Lower) = 1) and
            (Copy(Lower, Length(Lower) - 10, 11) = '/glpi-agent') and
            (Pos('?', Value) = 0) and (Pos('#', Value) = 0) and (Pos('@', Value) = 0) and
            (Pos(' ', Value) = 0) and (Pos('"', Value) = 0) and
            (Pos(#13, Value) = 0) and (Pos(#10, Value) = 0);
end;

function JsonEscape(Value: String): String;
begin
  Result := Value;
  StringChange(Result, '\', '\\');
  StringChange(Result, '"', '\"');
  StringChange(Result, #13, '');
  StringChange(Result, #10, '');
end;

procedure RemoveOneTimeConfig();
begin
  if (OneTimeConfigPath <> '') and FileExists(OneTimeConfigPath) then begin
    DeleteFile(OneTimeConfigPath);
  end;
end;

procedure InitializeWizard;
var
  ExistingGateway: String;
  ExistingTag: String;
begin
  GatewayPage := CreateInputQueryPage(wpSelectDir,
    'Подключение к AssetGuard',
    'Укажите защищённый адрес сервера',
    'Адрес должен оканчиваться на /glpi-agent. Не используйте временный trycloudflare.com URL для постоянной установки.');
  GatewayPage.Add('Адрес сервера (HTTPS):', False);
  GatewayPage.Values[0] := 'https://';
  if ((RegQueryStringValue(HKLM64, 'SOFTWARE\GLPI-Agent', 'tag', ExistingTag) and
    (Pos('assetguard-installer-', ExistingTag) = 1)) or
    FileExists(ExpandConstant('{commonappdata}\AssetGuard\glpi-agent-registry-acl.sddl'))) and
    RegQueryStringValue(HKLM64, 'SOFTWARE\GLPI-Agent', 'server', ExistingGateway) and
    IsValidGateway(ExistingGateway) then GatewayPage.Values[0] := ExistingGateway;

  EnrollmentPage := CreateInputOptionPage(GatewayPage.ID,
    'Сценарий подключения',
    'Новый компьютер или восстановление',
    'После переустановки Windows выберите восстановление: AssetGuard найдёт прежнюю карточку по SMBIOS UUID, а администратор подтвердит запрос.',
    True, False);
  EnrollmentPage.Add('Новое подключение — у меня есть выданные логин и ключ');
  EnrollmentPage.Add('Восстановление после переустановки Windows');
  EnrollmentPage.Add('Обновить Agent с сохранением текущего подключения');
  EnrollmentPage.Values[0] := True;
  if ExpandConstant('{param:UPGRADE|0}') = '1' then EnrollmentPage.Values[2] := True;

  CredentialPage := CreateInputQueryPage(EnrollmentPage.ID,
    'Учётные данные устройства',
    'Введите данные, выданные администратором AssetGuard',
    'Для каждого компьютера используйте отдельную пару логин и ключ. Ключ показывается только при создании устройства.');
  CredentialPage.Add('Логин устройства:', False);
  CredentialPage.Values[0] := 'assetguard';
  CredentialPage.Add('Ключ инвентаризации:', True);

  OptionsPage := CreateInputOptionPage(CredentialPage.ID,
    'Первичная инвентаризация',
    'Первая отправка данных',
    'Agent работает автоматически вместе с Windows, сохраняет снимки без интернета и отправляет очередь после восстановления связи.',
    True, False);
  OptionsPage.Add('Отправить первую инвентаризацию сразу после установки');
  OptionsPage.Values[0] := True;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = CredentialPage.ID) and (EnrollmentPage.Values[1] or EnrollmentPage.Values[2]);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = GatewayPage.ID then begin
    if not IsValidGateway(GatewayPage.Values[0]) then begin
      MsgBox('Укажите адрес вида https://ваш-домен/glpi-agent без параметров.', mbError, MB_OK);
      Result := False;
    end;
  end;
  if (CurPageID = CredentialPage.ID) and Result and EnrollmentPage.Values[0] then begin
    if not IsValidUsername(CredentialPage.Values[0]) then begin
      MsgBox('Логин должен состоять из 3–128 латинских букв, цифр или дефисов.', mbError, MB_OK);
      Result := False;
    end else if Length(CredentialPage.Values[1]) < 12 then begin
      MsgBox('Ключ должен содержать не менее 12 символов.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  ConfigJson: String;
  PowerShell: String;
  RunNowJson: String;
  ReEnrolJson: String;
begin
  if CurStep = ssPostInstall then begin
    if EnrollmentPage.Values[2] then begin
      PowerShell := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
      if not Exec(PowerShell,
        '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\update-assetguard-agent.ps1') + '" -GatewayUri "' + GatewayPage.Values[0] + '"',
        '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
        RaiseException('Не удалось обновить Agent. Проверьте существующее подключение и повторите установку.');
      Exit;
    end;
    if OptionsPage.Values[0] then RunNowJson := 'true' else RunNowJson := 'false';
    if EnrollmentPage.Values[1] then ReEnrolJson := 'true' else ReEnrolJson := 'false';
    OneTimeConfigPath := ExpandConstant('{app}\assetguard-install-once.json');
    ConfigJson := '{' + #13#10 +
      '  "installerVersion": "{#AppVersion}",' + #13#10 +
      '  "gatewayUri": "' + JsonEscape(GatewayPage.Values[0]) + '",' + #13#10 +
      '  "agentUsername": "' + JsonEscape(CredentialPage.Values[0]) + '",' + #13#10 +
      '  "inventorySecret": "' + JsonEscape(CredentialPage.Values[1]) + '",' + #13#10 +
      '  "reEnrol": ' + ReEnrolJson + ',' + #13#10 +
      '  "runInventoryNow": ' + RunNowJson + #13#10 +
      '}';
    SaveStringToFile(OneTimeConfigPath, ConfigJson, False);
    Exec(ExpandConstant('{cmd}'), '/c icacls "' + OneTimeConfigPath + '" /inheritance:r /grant:r "*S-1-5-18:(F)" "*S-1-5-32-544:(F)"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    if ResultCode <> 0 then begin
      RemoveOneTimeConfig();
      RaiseException('Не удалось защитить временный файл учётных данных. Установка отменена.');
    end;
    PowerShell := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
    if EnrollmentPage.Values[1] then
      MsgBox('Запрос на восстановление будет отправлен после нажатия OK. Администратор школы должен открыть «Подключить Agent» и подтвердить компьютер в течение 30 минут.', mbInformation, MB_OK);
    if not Exec(PowerShell,
      '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\install-assetguard-agent-from-config.ps1') + '" -ConfigPath "' + OneTimeConfigPath + '"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then begin
      RemoveOneTimeConfig();
      RaiseException('Не удалось установить службу AssetGuard Agent. Подробность сохранена в C:\\ProgramData\\AssetGuard\\last-agent-install-error.txt. Откройте этот файл от имени администратора или отправьте мне его скриншот.');
    end;
  end;
end;

procedure DeinitializeSetup();
begin
  RemoveOneTimeConfig();
end;
