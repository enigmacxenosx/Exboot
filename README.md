# Exboot

Exboot is a Windows bootable-media creator for Windows 11 installation ISOs. It uses built-in Windows utilities to mount an ISO, prepare a selected USB drive, copy the installation files, and split a large `install.wim` when required for FAT32 media.

## Included tool

- `Windows11_Bootable_USB_Creator.bat` — administrator batch utility with ISO selection, disk listing, explicit `ERASE` confirmation, GPT/FAT32 formatting, file copying, and installation-image splitting.

## Requirements

Exboot requires Windows 10 or Windows 11, Administrator privileges, a genuine Windows installation ISO, and a USB drive large enough for the installation media.

## Important warning

> The selected USB disk will be erased completely. Confirm the disk number carefully before typing `ERASE`, and back up any files on the USB drive first.

Exboot creates Windows installation media only. It does not activate Windows, bypass licensing, or provide a product key.

## Usage

1. Download a genuine Windows ISO from Microsoft.
2. Connect the USB drive and close applications that are using it.
3. Run `Windows11_Bootable_USB_Creator.bat` as Administrator.
4. Enter the ISO path when prompted.
5. Review the `diskpart` disk list and enter the correct USB disk number.
6. Type `ERASE` only after confirming that the selected disk is the USB drive.
7. Boot the target computer from the completed USB media.

## Status

This is the initial command-line version of Exboot. A graphical desktop interface can be added in a future version.
