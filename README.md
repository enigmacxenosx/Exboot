# Exboot

Exboot is a Windows desktop utility from **Enosx Technologies** for creating bootable Windows installation media from a genuine ISO. It provides a graphical workflow for selecting an ISO, identifying a USB disk, choosing a partition and boot mode, confirming destructive operations, copying installation files, and splitting large `install.wim` files for FAT32 compatibility.

## Capabilities

- Single-ISO Windows media creation with GPT/UEFI, MBR/UEFI, and MBR/BIOS Legacy layouts.
- Multi-boot USB creation through Ventoy for Windows, Linux, IMG, VHD, and VHDX images.
- Image freshness detection for Windows ISO, WIM, and ESD files.
- Optional Windows 11 TPM and Secure Boot compatibility settings.
- Appearance customization and GitHub Releases update checks with SHA-256 verification.

## Important safety notice

Exboot requires Administrator access and uses DiskPart, DISM, PowerShell disk-management commands, and Robocopy. Creating media **erases the selected USB disk completely**. Verify the disk number, model, and capacity and back up its contents before proceeding. Exboot does not activate Windows or bypass product-key licensing.

## Requirements

- Windows 10 or Windows 11.
- Python 3.10 or newer for local builds.
- A genuine Windows ISO and a USB drive with sufficient capacity.
- Inno Setup 6 to build the installer locally.

## Build the installer

On Windows, open PowerShell in the repository directory:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_installer.ps1
```

The installer is written to `installer-output\ExbootSetup-<version>.exe`. Tagged releases run the Windows GitHub Actions workflow and attach the installer to the corresponding GitHub Release.

## Development and validation

`exboot.py` contains the Tkinter application. `tests_freshness.py` covers image classification and freshness parsing. The quality-gates workflow runs linting and a headless GUI smoke test. Windows system utilities and the final installer must be built on Windows.

## Automatic updates

The application checks GitHub Releases after startup and every six hours. Updates require user confirmation, are matched to the release asset, verified against the published SHA-256 digest, and launched only after Exboot closes.

## License

Proprietary — © 2024–2026 Enosx Technologies. All rights reserved.
