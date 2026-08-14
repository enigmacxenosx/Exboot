# Multi-boot architecture findings

Ventoy’s official documentation states that after installation the USB is divided into two partitions, with a first data partition that can be formatted as exFAT or other supported filesystems. Users then copy ISO, WIM, IMG, or VHD(x) files to the data partition; Ventoy recursively discovers image files and lists them in the boot menu. The documentation warns that installation formats the USB and erases its data.

Source: https://www.ventoy.net/en/doc_start.html

The official Ventoy GitHub repository describes Ventoy as a bootable USB solution and exposes a GPL-3.0 license. This makes Ventoy-style integration feasible, but Exboot should either invoke an official Ventoy Windows package supplied by the user or download and verify a specific official release rather than copying Ventoy source into the Exboot repository without reviewing license obligations.

Source: https://github.com/ventoy/Ventoy

Recommended Exboot architecture: provide a Multi-boot mode that selects multiple ISO files, installs or updates an official Ventoy package on a selected USB disk, copies the selected ISO files to the data partition, and leaves boot-menu discovery to Ventoy. Keep the existing single-ISO workflow as a separate mode. Require Administrator privileges, show the target disk number/size/model, require an explicit erase confirmation, and verify downloaded package checksums before installation when Exboot performs the download.


The official Windows CLI documentation specifies the command format `Ventoy2Disk.exe VTOYCLI CMD DISK [Options]`, where CMD is `/I` for install or `/U` for update, and the physical disk can be specified with `/PhyDrive:N`. It supports `/GPT` for GPT partition style, `/NOSB` to disable Ventoy Secure Boot Support, `/VTOYALIGN`, `/R:XXX`, `/FS:XXX`, and `/NonDest`. Exboot should use `/I /PhyDrive:<disk_number> /GPT` for its default multi-boot install, keep Secure Boot support enabled unless the user explicitly chooses otherwise, and require the final erase confirmation before invoking Ventoy.

Source: https://www.ventoy.net/en/doc_windows_cli.html


Ventoy’s official theme plugin supports a `theme` object in `ventoy.json` whose `file` field points to a GRUB `theme.txt`, for example `/ventoy/theme/blur/theme.txt`. The theme folder can contain the theme definition and referenced background/image assets. Ventoy is GRUB2-based, so standard GRUB2 themes can be used. Exboot should create `/ventoy/ventoy.json`, `/ventoy/theme/exboot/theme.txt`, and copy the selected background image into the same theme directory, using a theme file with the user-selected colors and menu title.

Source: https://www.ventoy.net/en/plugin_theme.html
