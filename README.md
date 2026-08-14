# Exboot

Exboot is a Windows desktop utility for creating bootable Windows installation media from a genuine ISO. It provides a graphical workflow for selecting the ISO, identifying USB disks, confirming the destructive operation, formatting the selected disk, copying installation files, and splitting a large `install.wim` for FAT32 compatibility.

## Project files

| File | Purpose |
|---|---|
| `exboot.py` | Graphical desktop application implemented with Python and Tkinter |
| `build_windows.ps1` | Windows build script that packages Exboot as a portable executable with PyInstaller |
| `Windows11_Bootable_USB_Creator.bat` | Legacy command-line version |

## Requirements

Exboot is intended for Windows 10 or Windows 11. The application must run as Administrator because it uses DiskPart, DISM, PowerShell disk-management commands, and Robocopy. A genuine Windows ISO and a USB drive with sufficient capacity are required.

## Building the Windows executable

Install Python 3.10 or newer on Windows, open PowerShell in the project directory, and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

The generated portable executable will be placed in `dist\Exboot.exe`. The build script does not activate Windows, bypass licensing, or include a product key.

## Using Exboot

Run `Exboot.exe` as Administrator. Select a genuine Windows ISO, choose the correct USB disk from the detected list, review the disk details, confirm the warning dialogs, and start creation. Exboot formats the selected USB drive as GPT/FAT32 and copies the installation files. The selected disk is erased completely.

> **Important:** Verify the target disk carefully and back up its contents before proceeding. Exboot cannot recover data erased from the selected drive.

## Status

This repository contains the first graphical desktop version of Exboot. The application source is validated for Python syntax. Windows executable packaging must be performed on Windows because the final executable depends on Windows system utilities.
