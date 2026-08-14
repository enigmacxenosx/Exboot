# Exboot

Exboot is a Windows desktop utility for creating bootable Windows installation media from a genuine ISO. It provides a graphical workflow for selecting the ISO, identifying USB disks, choosing a partition and boot mode, confirming the destructive operation, formatting the selected disk, copying installation files, and splitting a large `install.wim` for FAT32 compatibility.

## Enosx Technologies branding

The desktop interface includes an Enosx Technologies banner with the Exboot name, product subtitle, and Enosx color treatment. The branding is implemented directly in the Windows interface so the portable executable does not require a separate image asset.

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

Run `Exboot.exe` as Administrator. Select a genuine Windows ISO, choose the correct USB disk from the detected list, select a partition and boot mode, review the disk details, confirm the warning dialogs, and start creation. The selected disk is erased completely.

| Option | Partition table | File system | Intended boot mode |
|---|---|---|---|
| `GPT + UEFI` | GPT | FAT32 | Modern UEFI systems; recommended for most Windows 11 computers |
| `MBR + UEFI` | MBR | FAT32 | UEFI systems that require MBR-formatted removable media |
| `MBR + BIOS / Legacy` | MBR | NTFS | Older systems using legacy BIOS/CSM boot |

The GPT/UEFI option is the default. The MBR/BIOS Legacy option also marks the USB partition active. Firmware compatibility varies by computer, so choose the option that matches the target system's boot configuration.

Exboot also provides an optional **Bypass Windows 11 TPM and Secure Boot checks** setting. When enabled, it mounts the USB `sources\boot.wim` image and adds `BypassTPMCheck=1` and `BypassSecureBootCheck=1` under the offline Setup `LabConfig` registry key. This setting is disabled by default and should be used only on hardware you own or administer. It does not activate Windows or bypass product-key licensing, and bypassing these checks can reduce hardware-security protections.

> **Important:** Verify the target disk carefully and back up its contents before proceeding. Exboot cannot recover data erased from the selected drive.

## Status

This repository contains the Enosx Technologies branded graphical desktop version of Exboot with selectable GPT/UEFI, MBR/UEFI, and MBR/BIOS Legacy media layouts, plus an optional TPM and Secure Boot compatibility setting. The application source is validated for Python syntax. Windows executable packaging must be performed on Windows because the final executable depends on Windows system utilities.
