# Exboot

Exboot is a Windows desktop utility from **Enosx Technologies** for creating bootable Windows installation media from a genuine ISO. It provides a graphical workflow for selecting the ISO, identifying USB disks, choosing a partition and boot mode, confirming the destructive operation, formatting the selected disk, copying installation files, and splitting a large `install.wim` for FAT32 compatibility.

## Updates

Exboot checks the public GitHub Releases endpoint for `enigmacxenosx/Exboot` shortly after startup, repeats the check every six hours while the application is open, and also provides a **Check for updates** button. The checker compares the installed application version with the latest release tag, selects the matching `ExbootSetup-{version}.exe` asset, and displays release notes before asking whether to download it. The downloaded installer is size-checked and verified against the SHA-256 digest published with the GitHub release asset before Exboot asks whether to launch it. Exboot closes before the installer starts, and it never silently replaces the running application.

The current application version is `0.3.2`. Publish future builds with semantic-style tags such as `v0.3.2` or `v0.4.0` so the checker can compare them correctly. The installer and executable use the Enosx AI splash logo from `assets/enosx-ai-splash-logo.ico`, with matching wizard artwork from `assets/enosx-ai-splash-wizard.png`.

## Version 0.3.2

Version 0.3.2 adds a safe automatic update workflow. Exboot checks GitHub Releases, downloads only the matching single-file setup executable after confirmation, verifies its SHA-256 checksum, and closes before launching the installer.

## Version 0.3.1

Version 0.3.1 extends multi-boot mode with **Linux and other non-Windows image support**. Ventoy-compatible live ISOs such as Ubuntu-family `casper` images and other distributions, diagnostic media, and IMG files can now be added alongside Windows installers. Each image's detected family is shown in the multi-boot image list and the activity log, and the selection label reflects mixed Windows and Linux content.

The release also adds **image freshness detection**. When a Windows ISO or WIM/ESD file is selected, Exboot reads the build timestamp and WIM header version directly from `install.wim` or `install.esd` inside the image and displays the build date with a Fresh / Dated / Outdated assessment in the ISO panel and the activity log. Non-Windows media keep the panel silent so the label never shows placeholder text.

Image classification and freshness parsing are covered by unit tests in `tests_freshness.py`, which run together with the lint and GUI smoke-test gates defined in `.github/workflows/quality-gates.yml`.

## Appearance customization

The **Appearance** control provides a dark-mode toggle and a custom accent-color picker. The selected settings are stored per user under the Windows application-data folder and restored automatically at the next launch. The accent color is applied to the Enosx Technologies banner, action controls, and active control states.

## Enosx Technologies branding

The desktop interface includes an Enosx Technologies banner with the Exboot name, product subtitle, and Enosx color treatment. The installer now carries the Enosx AI splash treatment: a dark glass EX mark, cyan glow, `from Enosx Technologies` footer, and cyan progress accent. The same square splash logo is embedded into the Windows executable and used as the installer icon.

## Project files

| File | Purpose |
|---|---|
| `exboot.py` | Branded graphical desktop application implemented with Python and Tkinter |
| `build_windows.ps1` | Builds the portable `dist\\Exboot.exe` application on Windows with the branded icon |
| `assets/enosx-ai-splash-logo.ico` | Multi-resolution Enosx AI splash icon used by the executable and installer |
| `assets/enosx-ai-splash-wizard.png` | Enosx AI splash artwork used on the installer welcome and completion pages |
| `assets/create_enosx_ai_splash_assets.py` | Generates the Enosx AI splash PNG and multi-resolution ICO assets |
| `build_installer.ps1` | Builds the executable and packages it with Inno Setup |
| `installer.iss` | Standard Windows installer definition |
| `.github/workflows/build-installer.yml` | Builds and attaches the single installer executable to tagged GitHub Releases |
| `.github/workflows/quality-gates.yml` | Runs linting and a headless GUI smoke test on every push and pull request |
| `Windows11_Bootable_USB_Creator.bat` | Legacy command-line version |
| `multiboot_research.md` | Architecture notes and official Ventoy references |
| `tests_freshness.py` | Unit tests for image classification and Windows build freshness detection |

## Requirements

Exboot is intended for Windows 10 or Windows 11. The application must run as Administrator because it uses DiskPart, DISM, PowerShell disk-management commands, and Robocopy. A genuine Windows ISO and a USB drive with sufficient capacity are required.

## Building the installer locally

On a Windows PC, install Python 3.10 or newer and [Inno Setup 6](https://jrsoftware.org/isinfo.php). Open PowerShell in the project directory and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_installer.ps1
```

The installer will be created as the single setup executable `installer-output\\ExbootSetup-0.3.2.exe`. It uses the Enosx AI logo as its Windows file icon, installs Exboot under Program Files, creates a Start Menu shortcut, optionally creates a desktop shortcut, and can launch Exboot after installation. GitHub publishes the installer asset’s SHA-256 digest, which the automatic updater uses to verify downloads.

## Automated release builds

Pushing a version tag such as `v0.3.2` starts the Windows GitHub Actions build. The workflow builds `Exboot.exe`, installs Inno Setup on the Windows runner, creates the single installer executable, stores it as a workflow artifact, and attaches only that `.exe` to the matching GitHub Release. The repository must have Actions enabled and permission to write release contents.

## Multi-boot USB mode

Select **Multi-boot USB (Ventoy)** from the Creation mode control to place multiple operating-system images on one USB. Add ISO, WIM, IMG, VHD, or VHDX files, select **Theme settings…** to choose a menu title, background image, and GRUB menu colors, then confirm the two-step erase warning. Exboot downloads the latest official Ventoy Windows package from the Ventoy GitHub Releases endpoint, verifies its SHA-256 checksum from the accompanying `sha256.txt`, installs Ventoy in GPT mode through the documented Windows CLI, and copies the selected image files into an `Exboot Images` folder on the Ventoy data partition. Ventoy then discovers the files and presents them in its styled boot menu at startup. Exboot writes `ventoy/ventoy.json`, `ventoy/theme/exboot/theme.txt`, and the selected background image into the USB data partition. PNG and JPEG backgrounds are supported.

Multi-boot mode is intentionally separate from the single Windows installer mode. The Ventoy installation formats the selected USB disk and erases all existing data. Only use it with a USB drive you have backed up and verified by disk number, model, and capacity. Exboot does not silently download or install images, and it does not bypass operating-system licensing.

Exboot uses the official Ventoy Windows release package for the multi-boot engine. Ventoy is an open-source project distributed under GPL-3.0. Exboot downloads the package from the official Ventoy GitHub Releases endpoint at runtime and verifies its published SHA-256 checksum before invoking `Ventoy2Disk.exe`. See the [Ventoy project](https://github.com/ventoy/Ventoy), the [Ventoy startup guide](https://www.ventoy.net/en/doc_start.html), and the [Ventoy Windows CLI documentation](https://www.ventoy.net/en/doc_windows_cli.html) for details.

## ISO integrity verification

Before creating either single-ISO or multi-boot media, use the **Integrity verification** panel. Choose **SHA-256** or **MD5**, enter the expected hexadecimal digest, or load a standard checksum/manifest text file with **Checksum file…**, and press **Verify**. Exboot calculates the digest in a background worker using streaming reads, reports the result in the activity log, and blocks the creation workflow unless the selected files match the expected values. In multi-boot mode, a checksum manifest can contain one matching filename and digest per selected image.

SHA-256 is recommended for modern integrity verification. MD5 is retained for compatibility with older vendor checksum files and should not be treated as a modern collision-resistant security signature. Exboot compares the complete digest before writing any data to the USB.

## USB speed benchmark

After a successful single-ISO or multi-boot creation, enable **Run sequential read/write benchmark after creation** to measure the selected USB drive. Choose a temporary test size from 256 MB, 512 MB, 1 GB, or 2 GB. Exboot writes the test file sequentially, flushes it, reads it back sequentially, reports write and read throughput in MiB/s, and removes the temporary file in a cleanup step. The benchmark is optional, requires confirmation, and does not alter the installed operating-system images.

Benchmark numbers vary with the USB controller, port, filesystem, drive fullness, thermal throttling, and operating-system caching. They are useful for relative comparison, not as a guarantee of sustained performance in every workload. Keep sufficient free space available and do not disconnect the USB drive while the test is running.

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
