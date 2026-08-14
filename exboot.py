import ctypes
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import webbrowser
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

APP_NAME = "Exboot"
APP_VERSION = "0.1.1"
GITHUB_RELEASES_URL = "https://api.github.com/repos/enigmacxenosx/Exboot/releases/latest"


def run_command(args, check=True, capture=True):
    return subprocess.run(
        args,
        text=True,
        capture_output=capture,
        check=check,
        encoding="utf-8",
        errors="replace",
    )


def ps(command):
    return run_command(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command])


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def format_size(value):
    try:
        size = float(value)
    except (TypeError, ValueError):
        return "Unknown size"
    for unit in ("B", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return "Unknown size"


class ExbootApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Exboot — Windows Bootable USB Creator")
        self.geometry("860x700")
        self.minsize(760, 620)
        self.resizable(True, True)
        self.configure(bg="#f3f6fb")
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("Card.TLabelframe", padding=12)
        style.configure("Card.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        self.disks = []
        self.iso_path = tk.StringVar()
        self.selected_disk = tk.StringVar()
        self.partition_mode = tk.StringVar(value="GPT + UEFI")
        self.bypass_checks = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Ready")
        self.build_ui()
        self.refresh_disks()
        self.after(1200, lambda: self.check_for_updates(show_no_update=False))

    def build_ui(self):
        outer = ttk.Frame(self, padding=(20, 18), style="TFrame")
        outer.pack(fill="both", expand=True)

        banner = tk.Canvas(outer, height=92, highlightthickness=0, bd=0, bg="#102a43")
        banner.pack(fill="x", pady=(0, 18))
        banner.bind("<Configure>", self.draw_banner)
        self.banner = banner

        iso_frame = ttk.LabelFrame(outer, text="1. Windows ISO", padding=12, style="Card.TLabelframe")
        iso_frame.pack(fill="x", pady=(0, 12))
        ttk.Entry(iso_frame, textvariable=self.iso_path).pack(side="left", fill="x", expand=True)
        ttk.Button(iso_frame, text="Browse…", command=self.choose_iso).pack(side="left", padx=(8, 0))

        disk_frame = ttk.LabelFrame(outer, text="2. Target USB drive", padding=12, style="Card.TLabelframe")
        disk_frame.pack(fill="x", pady=(0, 12))
        self.disk_combo = ttk.Combobox(
            disk_frame, textvariable=self.selected_disk, state="readonly"
        )
        self.disk_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(disk_frame, text="Refresh", command=self.refresh_disks).pack(side="left", padx=(8, 0))

        mode_frame = ttk.LabelFrame(outer, text="3. Partition scheme and boot mode", padding=12, style="Card.TLabelframe")
        mode_frame.pack(fill="x", pady=(0, 12))
        self.mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.partition_mode,
            state="readonly",
            values=("GPT + UEFI", "MBR + UEFI", "MBR + BIOS / Legacy"),
        )
        self.mode_combo.pack(side="left", fill="x", expand=True)
        ttk.Label(
            mode_frame,
            text="GPT/UEFI is recommended for modern Windows 11 systems.",
        ).pack(side="left", padx=(12, 0))

        bypass_frame = ttk.LabelFrame(outer, text="4. Optional compatibility settings", padding=12, style="Card.TLabelframe")
        bypass_frame.pack(fill="x", pady=(0, 12))
        ttk.Checkbutton(
            bypass_frame,
            text="Bypass Windows 11 TPM and Secure Boot checks",
            variable=self.bypass_checks,
        ).pack(anchor="w")
        ttk.Label(
            bypass_frame,
            text="Modifies the USB boot image's LabConfig registry. Use only on hardware you own or administer.",
            foreground="#8a4b00",
        ).pack(anchor="w", pady=(5, 0))

        warning = ttk.Label(
            outer,
            text="WARNING: The selected USB drive will be erased completely. Verify the disk carefully.",
            foreground="#a00000",
            font=("Segoe UI", 10, "bold"),
            wraplength=700,
        )
        warning.pack(anchor="w", pady=(0, 12))

        action_frame = ttk.Frame(outer)
        action_frame.pack(fill="x", pady=(0, 12))
        ttk.Button(action_frame, text="Check for updates", command=lambda: self.check_for_updates(True)).pack(side="right")
        self.create_button = ttk.Button(
            action_frame, text="Create Bootable USB", command=self.start_creation, style="Accent.TButton"
        )
        self.create_button.pack(side="left")
        ttk.Label(action_frame, textvariable=self.status).pack(side="left", padx=14)

        log_frame = ttk.LabelFrame(outer, text="Progress and activity log", padding=8, style="Card.TLabelframe")
        log_frame.pack(fill="both", expand=True)
        self.log_box = tk.Text(log_frame, height=14, state="disabled", wrap="word", font=("Consolas", 9))
        self.log_box.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.log_box.yview)
        scroll.pack(side="right", fill="y")
        self.log_box.configure(yscrollcommand=scroll.set)

        ttk.Label(
            outer,
            text="Exboot creates installation media only. It does not activate Windows or bypass licensing.",
            font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(10, 0))

    def apply_labconfig_bypass(self, usb_drive):
        boot_wim = os.path.join(usb_drive + "\\", "sources", "boot.wim")
        if not os.path.exists(boot_wim):
            raise RuntimeError("Cannot enable the bypass: sources\\boot.wim was not found on the USB.")
        mount_dir = tempfile.mkdtemp(prefix="exboot_bootwim_")
        mounted = False
        hive_loaded = False
        try:
            self.log("Applying TPM and Secure Boot LabConfig values to boot.wim…")
            mount_result = run_command(
                ["dism.exe", "/Mount-Image", f"/ImageFile:{boot_wim}", "/Index:2", f"/MountDir:{mount_dir}"],
                check=False,
            )
            if mount_result.returncode != 0:
                raise RuntimeError(mount_result.stdout + mount_result.stderr)
            mounted = True
            hive_path = os.path.join(mount_dir, "Windows", "System32", "Config", "SYSTEM")
            load_result = run_command(["reg.exe", "load", r"HKLM\ExbootLabConfig", hive_path], check=False)
            if load_result.returncode != 0:
                raise RuntimeError(load_result.stdout + load_result.stderr)
            hive_loaded = True
            for value in ("BypassTPMCheck", "BypassSecureBootCheck"):
                add_result = run_command(
                    ["reg.exe", "add", r"HKLM\ExbootLabConfig\Setup\LabConfig", "/v", value, "/t", "REG_DWORD", "/d", "1", "/f"],
                    check=False,
                )
                if add_result.returncode != 0:
                    raise RuntimeError(add_result.stdout + add_result.stderr)
            run_command(["reg.exe", "unload", r"HKLM\ExbootLabConfig"], check=False)
            hive_loaded = False
            commit_result = run_command(
                ["dism.exe", "/Unmount-Image", f"/MountDir:{mount_dir}", "/Commit"],
                check=False,
            )
            mounted = False
            if commit_result.returncode != 0:
                raise RuntimeError(commit_result.stdout + commit_result.stderr)
            self.log("TPM and Secure Boot bypass values applied successfully.")
        finally:
            if hive_loaded:
                run_command(["reg.exe", "unload", r"HKLM\ExbootLabConfig"], check=False)
            if mounted:
                run_command(["dism.exe", "/Unmount-Image", f"/MountDir:{mount_dir}", "/Discard"], check=False)
            try:
                os.rmdir(mount_dir)
            except OSError:
                pass

    def draw_banner(self, event=None):
        width = self.banner.winfo_width()
        height = self.banner.winfo_height()
        self.banner.delete("all")
        self.banner.create_rectangle(0, 0, width, height, fill="#102a43", outline="")
        self.banner.create_rectangle(0, height - 6, width, height, fill="#2bb3a3", outline="")
        self.banner.create_oval(width - 150, -90, width + 40, 100, fill="#173f5f", outline="")
        self.banner.create_oval(width - 95, -50, width + 75, 120, fill="#1c6e8c", outline="")
        self.banner.create_text(24, 29, anchor="w", text="ENOSX TECHNOLOGIES", fill="#8ee3d5", font=("Segoe UI", 11, "bold"))
        self.banner.create_text(24, 59, anchor="w", text="Exboot", fill="white", font=("Segoe UI", 24, "bold"))
        self.banner.create_text(width - 24, 48, anchor="e", text="Windows Bootable USB Creator", fill="#d9eaf7", font=("Segoe UI", 10))

    def log(self, text):
        def append():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", text.rstrip() + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, append)

    @staticmethod
    def version_tuple(value):
        cleaned = value.strip().lower().lstrip("v")
        parts = []
        for item in cleaned.split("."):
            digits = "".join(character for character in item if character.isdigit())
            parts.append(int(digits or 0))
        return tuple((parts + [0, 0, 0])[:3])

    def check_for_updates(self, show_no_update=True):
        self.status.set("Checking for updates…")
        threading.Thread(target=self._check_for_updates_worker, args=(show_no_update,), daemon=True).start()

    def _check_for_updates_worker(self, show_no_update):
        try:
            request = urllib.request.Request(
                GITHUB_RELEASES_URL,
                headers={"Accept": "application/vnd.github+json", "User-Agent": "Exboot-Update-Checker"},
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                release = json.loads(response.read().decode("utf-8"))
            tag = release.get("tag_name", "").strip()
            release_url = release.get("html_url", "https://github.com/enigmacxenosx/Exboot/releases")
            notes = release.get("body") or "No release notes were provided."
            is_newer = bool(tag) and self.version_tuple(tag) > self.version_tuple(APP_VERSION)
            self.after(0, lambda: self._show_update_result(is_newer, tag, release_url, notes, show_no_update))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            self.after(0, lambda: self._show_update_error(str(exc), show_no_update))

    def _show_update_result(self, is_newer, tag, release_url, notes, show_no_update):
        self.status.set(f"Update available: {tag}" if is_newer else "Up to date")
        if is_newer:
            short_notes = notes[:1200] + ("…" if len(notes) > 1200 else "")
            open_release = messagebox.askyesno(
                "Exboot update available",
                f"A newer release ({tag}) is available.\n\nRelease notes:\n{short_notes}\n\nOpen the GitHub release page to download it?",
            )
            if open_release:
                webbrowser.open(release_url)
        elif show_no_update:
            messagebox.showinfo("Exboot updates", f"You are running the latest release ({APP_VERSION}).")

    def _show_update_error(self, error, show_no_update):
        self.status.set("Update check unavailable")
        if show_no_update:
            messagebox.showwarning(
                "Exboot updates",
                "Exboot could not check GitHub Releases right now. Please check your internet connection or visit the repository manually.",
            )
        self.log(f"Update check unavailable: {error}")

    def choose_iso(self):
        path = filedialog.askopenfilename(
            title="Select Windows ISO",
            filetypes=[("ISO images", "*.iso"), ("All files", "*.*")],
        )
        if path:
            self.iso_path.set(path)

    def refresh_disks(self):
        try:
            command = (
                "Get-Disk | Where-Object {$_.BusType -eq 'USB'} | "
                "Select-Object Number,FriendlyName,Size,PartitionStyle,OperationalStatus | "
                "ConvertTo-Json -Compress"
            )
            result = ps(command)
            raw = result.stdout.strip()
            data = [] if not raw else json.loads(raw)
            if isinstance(data, dict):
                data = [data]
            self.disks = data
            labels = []
            for disk in data:
                labels.append(
                    f"Disk {disk.get('Number')} — {disk.get('FriendlyName', 'USB drive')} — "
                    f"{format_size(disk.get('Size'))} — {disk.get('OperationalStatus', '')}"
                )
            self.disk_combo["values"] = labels
            if labels:
                self.disk_combo.current(0)
                self.log(f"Detected {len(labels)} USB disk(s).")
            else:
                self.selected_disk.set("")
                self.log("No USB disks detected. Connect a USB drive and click Refresh.")
        except Exception as exc:
            self.log(f"Could not enumerate USB disks: {exc}")

    def start_creation(self):
        if not is_admin():
            messagebox.showerror("Administrator required", "Run Exboot as Administrator before creating USB media.")
            return
        iso = self.iso_path.get().strip()
        index = self.disk_combo.current()
        if not iso or not Path(iso).is_file():
            messagebox.showerror("ISO required", "Select a valid Windows ISO file first.")
            return
        if index < 0 or index >= len(self.disks):
            messagebox.showerror("USB required", "Select a detected USB disk first.")
            return
        disk = self.disks[index]
        disk_number = str(disk.get("Number"))
        disk_name = self.disk_combo.get()
        confirmed = messagebox.askyesno(
            "Confirm erase",
            f"Exboot will erase ALL data on:\n\n{disk_name}\n\nSelected mode: {self.partition_mode.get()}\nTPM/Secure Boot bypass: {'ON' if self.bypass_checks.get() else 'OFF'}\n\nDo you want to continue?",
            icon="warning",
        )
        if not confirmed:
            return
        typed = simpledialog.askstring(
            "Final confirmation", "Type ERASE to confirm that the selected USB disk may be erased:"
        )
        if typed != "ERASE":
            self.log("Operation cancelled: confirmation text did not match.")
            return
        self.create_button.configure(state="disabled")
        self.status.set("Working…")
        threading.Thread(
            target=self.create_media,
            args=(iso, disk_number, self.partition_mode.get(), self.bypass_checks.get()),
            daemon=True,
        ).start()

    def create_media(self, iso, disk_number, mode, bypass_checks):
        mounted = False
        iso_drive = None
        try:
            self.log("Mounting ISO…")
            ps(f"Mount-DiskImage -ImagePath {json.dumps(iso)} -ErrorAction Stop")
            mounted = True
            drive_result = ps(
                f"(Get-DiskImage -ImagePath {json.dumps(iso)} | Get-Volume).DriveLetter"
            )
            iso_drive = drive_result.stdout.strip().splitlines()[0] + ":"
            if not os.path.exists(os.path.join(iso_drive + "\\", "sources", "install.wim")) and not os.path.exists(
                os.path.join(iso_drive + "\\", "sources", "install.esd")
            ):
                raise RuntimeError("The ISO does not contain a Windows install image.")
            self.log(f"ISO mounted at {iso_drive}")

            if mode == "GPT + UEFI":
                partition_scheme = "gpt"
                filesystem = "fat32"
            elif mode == "MBR + UEFI":
                partition_scheme = "mbr"
                filesystem = "fat32"
            else:
                partition_scheme = "mbr"
                filesystem = "ntfs"

            script = "\n".join(
                [
                    f"select disk {disk_number}",
                    "clean",
                    f"convert {partition_scheme}",
                    "create partition primary",
                    f"format fs={filesystem} quick label=WIN11",
                    "assign",
                    "exit",
                ]
            )
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="ascii") as handle:
                handle.write(script)
                diskpart_script = handle.name
            try:
                self.log(f"Formatting Disk {disk_number} as {partition_scheme.upper()}/{filesystem.upper()} for {mode}…")
                result = run_command(["diskpart.exe", "/s", diskpart_script], check=False)
                if result.returncode != 0:
                    raise RuntimeError(result.stdout + result.stderr)
            finally:
                os.unlink(diskpart_script)

            usb_result = ps("(Get-Volume -FileSystemLabel WIN11).DriveLetter")
            usb_drive = usb_result.stdout.strip().splitlines()[0] + ":"
            self.log(f"USB assigned as {usb_drive}")
            self.log("Copying Windows files…")
            copy_result = run_command(
                ["robocopy.exe", iso_drive + "\\", usb_drive + "\\", "/E", "/R:2", "/W:2", "/XF", "install.wim", "install.esd"],
                check=False,
            )
            if copy_result.returncode >= 8:
                raise RuntimeError(copy_result.stdout + copy_result.stderr)

            wim = iso_drive + "\\sources\\install.wim"
            if os.path.exists(wim):
                self.log("Splitting install.wim for FAT32 compatibility…")
                result = run_command(
                    ["dism.exe", "/Split-Image", f"/ImageFile:{wim}", f"/SWMFile:{usb_drive}\\sources\\install.swm", "/FileSize:3800"],
                    check=False,
                )
                if result.returncode != 0:
                    raise RuntimeError(result.stdout + result.stderr)
            else:
                self.log("Copying install.esd…")
                source = iso_drive + "\\sources\\install.esd"
                target = usb_drive + "\\sources\\install.esd"
                with open(source, "rb") as src, open(target, "wb") as dst:
                    while chunk := src.read(1024 * 1024):
                        dst.write(chunk)

            if bypass_checks:
                self.apply_labconfig_bypass(usb_drive)

            if mode == "MBR + BIOS / Legacy":
                self.log("Marking the MBR USB partition active for BIOS/Legacy boot…")
                active_script = f"select disk {disk_number}\nselect partition 1\nactive\nexit\n"
                with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="ascii") as handle:
                    handle.write(active_script)
                    active_path = handle.name
                try:
                    run_command(["diskpart.exe", "/s", active_path], check=False)
                finally:
                    os.unlink(active_path)
            self.log(f"Completed successfully using {mode}.")
            self.after(0, lambda: messagebox.showinfo("Exboot", "Bootable Windows USB creation completed."))
        except Exception as exc:
            self.log(f"ERROR: {exc}")
            self.after(0, lambda: messagebox.showerror("Exboot failed", str(exc)))
        finally:
            if mounted:
                ps(f"Dismount-DiskImage -ImagePath {json.dumps(iso)}")
            self.after(0, lambda: self.create_button.configure(state="normal"))
            self.after(0, lambda: self.status.set("Ready"))


if __name__ == "__main__":
    if sys.platform != "win32":
        print("Exboot must run on Windows.")
        raise SystemExit(1)
    app = ExbootApp()
    app.mainloop()
