@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Windows 11 Bootable USB Creator
color 0A

:: This script erases the selected USB disk. Run as Administrator.
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Administrator privileges are required.
    echo Right-click this file and select "Run as administrator".
    pause
    exit /b 1
)

where powershell.exe >nul 2>&1 || (
    echo [ERROR] PowerShell was not found.
    pause
    exit /b 1
)
where diskpart.exe >nul 2>&1 || (
    echo [ERROR] DiskPart was not found.
    pause
    exit /b 1
)
where dism.exe >nul 2>&1 || (
    echo [ERROR] DISM was not found.
    pause
    exit /b 1
)

set "ISO_PATH="
echo.
set /p "ISO_PATH=Enter the full path to the Windows 11 ISO file: "
if not exist "%ISO_PATH%" (
    echo [ERROR] The ISO file was not found.
    pause
    exit /b 1
)

set "ISO_PATH=%ISO_PATH:"=%"
set "ISO_DRIVE="
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Mount-DiskImage -ImagePath $env:ISO_PATH -ErrorAction Stop" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Windows could not mount the ISO.
    pause
    exit /b 1
)

for /f "delims=" %%I in ('powershell.exe -NoProfile -Command "$p=$env:ISO_PATH; (Get-DiskImage -ImagePath $p ^| Get-Volume).DriveLetter"') do set "ISO_DRIVE=%%I:"
if not defined ISO_DRIVE (
    echo [ERROR] Could not determine the mounted ISO drive letter.
    powershell.exe -NoProfile -Command "Dismount-DiskImage -ImagePath $env:ISO_PATH" >nul 2>&1
    pause
    exit /b 1
)

if not exist "!ISO_DRIVE!\sources\install.wim" if not exist "!ISO_DRIVE!\sources\install.esd" (
    echo [ERROR] The mounted ISO does not appear to contain Windows installation files.
    powershell.exe -NoProfile -Command "Dismount-DiskImage -ImagePath $env:ISO_PATH" >nul 2>&1
    pause
    exit /b 1
)

echo.
echo [INFO] Mounted ISO detected at !ISO_DRIVE!
echo.
echo Available disks:
echo list disk > "%TEMP%\w11_list_disk.txt"
diskpart /s "%TEMP%\w11_list_disk.txt"
del "%TEMP%\w11_list_disk.txt" >nul 2>&1

echo.
set "DISK_NUMBER="
set /p "DISK_NUMBER=Enter the USB disk number shown above: "
if not defined DISK_NUMBER goto :invalid_disk

set "CONFIRM="
echo.
echo WARNING: ALL DATA ON DISK !DISK_NUMBER! WILL BE ERASED.
set /p "CONFIRM=Type ERASE to continue: "
if /i not "!CONFIRM!"=="ERASE" (
    echo [INFO] Operation cancelled.
    powershell.exe -NoProfile -Command "Dismount-DiskImage -ImagePath $env:ISO_PATH" >nul 2>&1
    pause
    exit /b 0
)

:: Clean the selected disk and create one FAT32 GPT partition.
(
    echo select disk !DISK_NUMBER!
    echo clean
    echo convert gpt
    echo create partition primary
    echo format fs=fat32 quick label=WIN11
    echo assign
    echo exit
) > "%TEMP%\w11_diskpart.txt"
diskpart /s "%TEMP%\w11_diskpart.txt"
set "DP_ERROR=%errorlevel%"
del "%TEMP%\w11_diskpart.txt" >nul 2>&1
if not "%DP_ERROR%"=="0" goto :failed

set "USB_DRIVE="
for /f "delims=" %%I in ('powershell.exe -NoProfile -Command "(Get-Volume -FileSystemLabel WIN11).DriveLetter"') do set "USB_DRIVE=%%I:"
if not defined USB_DRIVE (
    echo [ERROR] Could not determine the formatted USB drive letter.
    goto :failed
)

echo.
echo [INFO] Copying Windows files to !USB_DRIVE! ...
robocopy "!ISO_DRIVE!\" "!USB_DRIVE!\" /E /R:2 /W:2 /XF install.wim install.esd
if errorlevel 8 goto :failed

:: FAT32 cannot store a file larger than 4 GB, so split install.wim when needed.
if exist "!ISO_DRIVE!\sources\install.wim" (
    echo [INFO] Creating split installation image on the FAT32 USB...
    dism /Split-Image /ImageFile:"!ISO_DRIVE!\sources\install.wim" /SWMFile:"!USB_DRIVE!\sources\install.swm" /FileSize:3800
    if errorlevel 1 goto :failed
) else (
    echo [INFO] Copying install.esd to the USB...
    copy /y "!ISO_DRIVE!\sources\install.esd" "!USB_DRIVE!\sources\install.esd" >nul
    if errorlevel 1 goto :failed
)

:: Mark the USB partition active for legacy BIOS compatibility when supported.
(
    echo select disk !DISK_NUMBER!
    echo select partition 1
    echo active
    echo exit
) > "%TEMP%\w11_active.txt"
diskpart /s "%TEMP%\w11_active.txt" >nul
del "%TEMP%\w11_active.txt" >nul 2>&1

powershell.exe -NoProfile -Command "Dismount-DiskImage -ImagePath $env:ISO_PATH" >nul 2>&1

echo.
echo [SUCCESS] Bootable Windows 11 USB creation completed.
echo [INFO] Restart the computer and boot from the USB drive.
pause
exit /b 0

:invalid_disk
echo [ERROR] No disk number was entered.
goto :cleanup

:failed
echo.
echo [ERROR] The USB creation process failed.

:cleanup
powershell.exe -NoProfile -Command "Dismount-DiskImage -ImagePath $env:ISO_PATH" >nul 2>&1
pause
exit /b 1
