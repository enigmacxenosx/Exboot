# Exboot

Exboot is a Windows desktop utility from **Enosx Technologies** for creating bootable Windows installation media from a genuine ISO. It provides a graphical workflow for selecting the ISO, identifying USB disks, choosing a partition and boot mode, confirming the destructive operation, formatting the selected disk, copying installation files, and splitting a large `install.wim` for FAT32 compatibility.

## Updates

Exboot checks the public GitHub Releases endpoint for `enigmacxenosx/Exboot` at startup and also provides a **Check for updates** button. The checker compares the installed application version with the latest release tag, displays release notes when a newer version is found, and opens the official GitHub release page only after the user confirms. It never silently downloads or replaces the executable.

The current application version is `0.1.5`. Publish future builds with semantic-style tags such as `v0.1.6` or `v0.2.0` so the checker can compare them correctly. The installer and executable use the EX-style Exboot icon from `assets/exboot.ico`, derived from the Enosx Technologies EX identity.

## Appearance customization

The **Appearance** control provides a dark-mode toggle and a custom accent-color picker. The selected settings are stored per user under the Windows application-data folder and restored automatically at the next launch. The accent color is applied to the Enosx Technologies banner, action controls, and active control states.

## Enosx Technologies branding

The desktop interface includes an Enosx Technologies banner with the Exboot name, product subtitle, and Enosx color treatment. The application icon now uses a stronger EX-style mark based on the supplied Enosx Technologies logo: angular cyan-blue geometry, a dark technical background, and a forward/boot motion cut. The branding is implemented directly in the Windows interface and packaging.

## Project files

| File | Purpose |
|---|---|
| `exboot.py` | Branded graphical desktop application implemented with Python and Tkinter |
| `build_windows.ps1` | Builds the portable `dist\\Exboot.exe` application on Windows with the branded icon |
| `assets/exboot.ico` | Multi-resolution Exboot application icon used by the executable and installer |
| `build_installer.ps1` | Builds the executable and packages it with Inno Setup |
| `installer.iss` | Standard Windows installer definition |
| `.github/workflows/build-installer.yml` | Builds the installer automatically on Windows and attaches it to tagged GitHub Releases |
| `Windows11_Bootable_USB_Creator.bat` | Legacy command-line version |

## Requirements

Exboot is intended for Windows 10 or Windows 11. The application must run as Administrator because it uses DiskPart, DISM, PowerShell disk-management commands, and Robocopy. A genuine Windows ISO and a USB drive with sufficient capacity are required.

## Building the installer locally

On a Windows PC, install Python 3.10 or newer and [Inno Setup 6](https://jrsoftware.org/isinfo.php). Open PowerShell in the project directory and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_installer.ps1
```

The installer will be created in `installer-output\\Exboot-Setup-0.1.5.exe`. It installs Exboot under Program Files, creates a Start Menu shortcut, optionally creates a desktop shortcut, and can launch Exboot after installation.

## Automated release builds

Pushing a version tag such as `v0.1.5` starts the Windows GitHub Actions build. The workflow builds `Exboot.exe`, installs Inno Setup on the Windows runner, creates the installer, stores it as a workflow artifact, and attaches it to the matching GitHub Release. The repository must have Actions enabled and permission to write release contents.

## Using Exboot

Run Exboot as Administrator. Select a genuine Windows ISO, choose the correct USB disk from the detected list, select a partition and boot mode, review the disk details, confirm the warning dialogs, and start creation. The selected disk is erased completely.

| Option | Partition table | File system | Intended boot mode |
|---|---|---|---|
| `GPT + UEFI` | GPT | FAT32 | Modern UEFI systems; recommended for most Windows 11 computers |
| `MBR + UEFI` | MBR | FAT32 | UEFI systems that require MBR-formatted removable media |
| `MBR + BIOS / Legacy` | MBR | NTFS | Older systems using legacy BIOS/CSM boot |

The GPT/UEFI option is the default. The MBR/BIOS Legacy option also marks the USB partition active. Firmware compatibility varies by computer, so choose the option that matches the target system's boot configuration.

Exboot also provides an optional **Bypass Windows 11 TPM and Secure Boot checks** setting. When enabled, it mounts the USB `sources\boot.wim` image and adds `BypassTPMCheck=1` and `BypassSecureBootCheck=1` under the offline Setup `LabConfig` registry key. This setting is disabled by default and should be used only on hardware you own or administer. It does not activate Windows or bypass product-key licensing, and bypassing these checks can reduce hardware-security protections.

> **Important:** Verify the target disk carefully and back up its contents before proceeding. Exboot cannot recover data erased from the selected drive.

## Status

This repository contains the Enosx Technologies branded graphical desktop version of Exboot with selectable GPT/UEFI, MBR/UEFI, and MBR/BIOS Legacy media layouts, optional TPM and Secure Boot compatibility settings, GitHub Releases update checking, and a standard Windows installer workflow. Source validation is performed in the development environment; the final executable and installer must be built on Windows because they depend on Windows system utilities.
