; Zope External Editor Inno Setup Script

[Setup]
DisableStartupPrompt=true
AppName=Zope External Editor Helper Application
AppVerName=Zope External Editor 0.12.7
AppPublisher=Thierry Benita, atReal contact@atreal.net (original version Casey Duncan, Zope Corporation)
AppPublisherURL=http://plone.org/products/zope-externaleditor-client
AppVersion=0.12.7
AppSupportURL=http://plone.org/products/zope-externaleditor-client
AppUpdatesURL=http://plone.org/products/zope-externaleditor-client
DefaultDirName={pf}\ZopeExternalEditor
DefaultGroupName=Zope External Editor
AllowNoIcons=true
LicenseFile=..\..\..\LICENSE.txt
ChangesAssociations=true
OutputBaseFilename=zopeedit-win32-0.12.7
VersionInfoCompany=atReal
AppID={{6A79A43D-B97B-4DA3-BD8D-2C4E84500D72}

[Registry]
; Register file type for use by helper app
Root: HKCR; SubKey: Zope.ExternalEditor; ValueType: string; ValueData: Zope External Editor; Flags: uninsdeletekeyifempty
Root: HKCR; SubKey: Zope.ExternalEditor; ValueType: binary; ValueName: EditFlags; ValueData: 00 00 01 00; Flags: uninsdeletevalue
Root: HKCR; SubKey: Zope.ExternalEditor\shell; Flags: uninsdeletekeyifempty
Root: HKCR; SubKey: Zope.ExternalEditor\shell\open; Flags: uninsdeletekeyifempty
Root: HKCR; SubKey: Zope.ExternalEditor\shell\open\command; ValueType: string; ValueData: """{app}\zopeedit.exe"" ""%1"""; Flags: uninsdeletekeyifempty
Root: HKCR; SubKey: .zope; ValueType: string; ValueData: Zope.ExternalEditor; Flags: uninsdeletekeyifempty
Root: HKCR; SubKey: .zope; ValueType: string; ValueName: PerceivedType; ValueData: Zope; Flags: uninsdeletevalue
Root: HKCR; SubKey: .zope; ValueType: string; ValueName: Content Type; ValueData: application/x-zope-edit; Flags: uninsdeletevalue
Root: HKCR; SubKey: .zem; ValueType: string; ValueData: Zope.ExternalEditor; Flags: uninsdeletekeyifempty
Root: HKCR; SubKey: .zem; ValueType: string; ValueName: PerceivedType; ValueData: Zope; Flags: uninsdeletevalue
Root: HKCR; SubKey: .zem; ValueType: string; ValueName: Content Type; ValueData: application/x-zope-edit; Flags: uninsdeletevalue
Root: HKCR; SubKey: MIME\Database\Content Type\application/x-zope-edit; ValueType: string; ValueName: Extension; ValueData: .zope; Flags: uninsdeletevalue
Root: HKCR; SubKey: MIME\Database\Content Type\application/x-zope-edit; ValueType: string; ValueName: Extension; ValueData: .zem; Flags: uninsdeletevalue
Root: HKCR; SubKey: MIME\Database\Content Type\application/x-zope-edit; Flags: uninsdeletekeyifempty
Root: HKLM; Subkey: SOFTWARE\Microsoft\Windows\CurrentVersion\ZopeExternalEditor\zopeedit.exe; ValueType: string; ValueName: Zope External Editor; ValueData: {app}\zopeedit.exe; Flags: uninsdeletekey

[Files]
Source: libs\*.*; DestDir: {app}; Flags: ignoreversion
Source: *.txt; DestDir: {app}; Flags: ignoreversion
Source: ZopeEdit.ini; DestDir: {app}; Flags: ignoreversion
Source: ZopeExtEditDummyOCX.ocx; DestDir: {app}; Flags: restartreplace regserver
Source: ..\..\..\README.txt; DestDir: {app}\docs; Flags: ignoreversion
Source: ..\..\..\LICENSE.txt; DestDir: {app}\docs; Flags: ignoreversion
Source: ..\..\..\docs\HISTORY.txt; DestDir: {app}\docs; Flags: ignoreversion
Source: ..\..\..\docs\VERSION.txt; DestDir: {app}\docs; Flags: ignoreversion
Source: ..\locales\en\LC_MESSAGES\*; DestDir: {app}\locales\en\LC_MESSAGES\; Flags: ignoreversion
Source: ..\locales\fr\LC_MESSAGES\*; DestDir: {app}\locales\fr\LC_MESSAGES\; Flags: ignoreversion
Source: ..\..\..\dist\*; DestDir: {app}; Flags: restartreplace
Source: ..\Plugins\*; DestDir: {app}\Plugins; Flags: ignoreversion

[_ISToolPreCompile]
Name: buildexe.bat; Parameters: ; Flags: abortonerror

[Icons]
Name: "{group}\ZopeEdit "; Filename: {app}\zopeedit.exe
