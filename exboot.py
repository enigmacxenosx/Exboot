import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk

APP_NAME = "Exboot"
APP_VERSION = "0.3.5"
AUTO_UPDATE_INTERVAL_MS = 6 * 60 * 60 * 1000
GITHUB_RELEASES_URL = (
    "https://api.github.com/repos/enigmacxenosx/Exboot/releases/latest"
)
VENTOY_RELEASES_URL = "https://api.github.com/repos/ventoy/Ventoy/releases/latest"


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
    return run_command(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ]
    )


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
        self.disks = []
        self.settings_path = (
            Path(os.environ.get("APPDATA", Path.home()))
            / "Enosx Technologies"
            / "Exboot"
            / "settings.json"
        )
        self.dark_mode = tk.BooleanVar(value=False)
        self.accent_color = "#2bb3a3"
        self.load_appearance_settings()
        self.apply_theme()
        self.disks = []
        self.iso_path = tk.StringVar()
        self.image_freshness = tk.StringVar(value="")
        self.selected_disk = tk.StringVar()
        self.partition_mode = tk.StringVar(value="GPT + UEFI")
        self.bypass_checks = tk.BooleanVar(value=False)
        self.media_mode = tk.StringVar(value="Single Windows installer")
        self.multi_iso_paths = []
        self.checksum_algorithm = tk.StringVar(value="SHA-256")
        self.checksum_expected = tk.StringVar()
        self.checksum_status = tk.StringVar(value="Not verified")
        self.verification_signature = None
        self.checksum_manifest_path = ""
        self.checksum_manifest = {}
        self.benchmark_after_creation = tk.BooleanVar(value=False)
        self.benchmark_size_mb = tk.StringVar(value="512 MB")
        self.last_notified_update = ""
        self.update_check_in_progress = False
        self.update_install_in_progress = False
        # Initialize widget references before build_ui so early mode changes cannot
        # raise AttributeError if a packaged or restored UI path is incomplete.
        self.disk_frame = None
        self.iso_frame = None
        self.mode_frame = None
        self.bypass_frame = None
        self.multi_frame = None
        self.warning_label = None
        self.theme_settings = {
            "title": "Enosx Technologies Exboot",
            "background": "",
            "background_color": "#061426",
            "text_color": "#dcecff",
            "selected_color": "#00d8ff",
            "version_color": "#7aa7d9",
        }
        self.status = tk.StringVar(value="Ready")
        self.build_ui()
        self.refresh_disks()
        self.after(
            1200, lambda: self.check_for_updates(show_no_update=False, automatic=True)
        )
        self.after(AUTO_UPDATE_INTERVAL_MS, self.periodic_update_check)

    def build_ui(self):
        outer = ttk.Frame(self, padding=(20, 18), style="TFrame")
        outer.pack(fill="both", expand=True)

        banner = tk.Canvas(outer, height=92, highlightthickness=0, bd=0, bg="#102a43")
        banner.pack(fill="x", pady=(0, 18))
        banner.bind("<Configure>", self.draw_banner)
        self.banner = banner

        media_mode_frame = ttk.LabelFrame(
            outer, text="Creation mode", padding=12, style="Card.TLabelframe"
        )
        media_mode_frame.pack(fill="x", pady=(0, 12))
        self.media_mode_combo = ttk.Combobox(
            media_mode_frame,
            textvariable=self.media_mode,
            state="readonly",
            values=("Single Windows installer", "Multi-boot USB (Ventoy)"),
        )
        self.media_mode_combo.pack(side="left", fill="x", expand=True)
        self.media_mode_combo.bind(
            "<<ComboboxSelected>>", lambda event: self.toggle_media_mode()
        )
        ttk.Label(
            media_mode_frame,
            text="Multi-boot mode supports multiple ISO/WIM/IMG/VHD files.",
        ).pack(side="left", padx=(12, 0))

        iso_frame = ttk.LabelFrame(
            outer, text="1. Windows ISO", padding=12, style="Card.TLabelframe"
        )
        iso_frame.pack(fill="x", pady=(0, 12))
        self.iso_frame = iso_frame
        ttk.Entry(iso_frame, textvariable=self.iso_path).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(iso_frame, text="Browse…", command=self.choose_iso).pack(
            side="left", padx=(8, 0)
        )
        ttk.Label(iso_frame, textvariable=self.image_freshness, foreground="#7a8aa0")

        checksum_frame = ttk.LabelFrame(
            outer, text="Integrity verification", padding=12, style="Card.TLabelframe"
        )
        checksum_frame.pack(fill="x", pady=(0, 12))
        self.checksum_frame = checksum_frame
        ttk.Label(checksum_frame, text="Algorithm:").pack(side="left")
        ttk.Combobox(
            checksum_frame,
            textvariable=self.checksum_algorithm,
            state="readonly",
            values=("SHA-256", "MD5"),
            width=10,
        ).pack(side="left", padx=(6, 12))
        ttk.Entry(checksum_frame, textvariable=self.checksum_expected, width=48).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(
            checksum_frame, text="Checksum file…", command=self.choose_checksum_file
        ).pack(side="left", padx=(6, 0))
        ttk.Button(checksum_frame, text="Verify", command=self.verify_checksums).pack(
            side="left", padx=(6, 0)
        )
        ttk.Label(checksum_frame, textvariable=self.checksum_status, width=22).pack(
            side="left", padx=(10, 0)
        )

        benchmark_frame = ttk.LabelFrame(
            outer,
            text="Post-creation USB benchmark",
            padding=12,
            style="Card.TLabelframe",
        )
        benchmark_frame.pack(fill="x", pady=(0, 12))
        self.benchmark_frame = benchmark_frame
        ttk.Checkbutton(
            benchmark_frame,
            text="Run sequential read/write benchmark after creation",
            variable=self.benchmark_after_creation,
        ).pack(side="left")
        ttk.Label(benchmark_frame, text="Test size:").pack(side="left", padx=(16, 6))
        ttk.Combobox(
            benchmark_frame,
            textvariable=self.benchmark_size_mb,
            state="readonly",
            values=("256 MB", "512 MB", "1 GB", "2 GB"),
            width=8,
        ).pack(side="left")
        ttk.Label(
            benchmark_frame, text="A temporary file is written, read, and deleted."
        ).pack(side="left", padx=(12, 0))

        self.disk_frame = ttk.LabelFrame(
            outer, text="2. Target USB drive", padding=12, style="Card.TLabelframe"
        )
        self.disk_frame.pack(fill="x", pady=(0, 12))
        self.disk_combo = ttk.Combobox(
            self.disk_frame, textvariable=self.selected_disk, state="readonly"
        )
        self.disk_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(self.disk_frame, text="Refresh", command=self.refresh_disks).pack(
            side="left", padx=(8, 0)
        )

        mode_frame = ttk.LabelFrame(
            outer,
            text="3. Partition scheme and boot mode",
            padding=12,
            style="Card.TLabelframe",
        )
        mode_frame.pack(fill="x", pady=(0, 12))
        self.mode_frame = mode_frame
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

        bypass_frame = ttk.LabelFrame(
            outer,
            text="4. Optional compatibility settings",
            padding=12,
            style="Card.TLabelframe",
        )
        bypass_frame.pack(fill="x", pady=(0, 12))
        self.bypass_frame = bypass_frame
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

        multi_frame = ttk.LabelFrame(
            outer, text="4. Multi-boot images", padding=12, style="Card.TLabelframe"
        )
        self.multi_frame = multi_frame
        multi_frame.pack(fill="x", pady=(0, 12))
        self.multi_list = tk.Listbox(
            multi_frame, height=5, selectmode=tk.EXTENDED, relief="flat", borderwidth=0
        )
        self.multi_list.pack(side="left", fill="both", expand=True)
        multi_buttons = ttk.Frame(multi_frame)
        multi_buttons.pack(side="left", padx=(10, 0), fill="y")
        ttk.Button(
            multi_buttons, text="Add ISO files…", command=self.add_multi_isos
        ).pack(fill="x")
        ttk.Button(
            multi_buttons, text="Remove selected", command=self.remove_multi_isos
        ).pack(fill="x", pady=(8, 0))
        ttk.Button(
            multi_buttons,
            text="Theme settings…",
            command=self.show_multiboot_theme_settings,
        ).pack(fill="x", pady=(8, 0))
        ttk.Label(
            multi_frame,
            text="Ventoy creates the boot menu automatically from the files copied to the USB.",
        ).pack(anchor="w", pady=(8, 0))

        self.warning_label = ttk.Label(
            outer,
            text="WARNING: The selected USB drive will be erased completely. Verify the disk carefully.",
            style="Warning.TLabel",
            font=("Segoe UI", 10, "bold"),
            wraplength=700,
        )
        self.warning_label.pack(anchor="w", pady=(0, 12))

        action_frame = ttk.Frame(outer)
        action_frame.pack(fill="x", pady=(0, 12))
        ttk.Button(
            action_frame, text="Appearance", command=self.show_appearance_settings
        ).pack(side="right", padx=(8, 0))
        ttk.Button(
            action_frame,
            text="Check for updates",
            command=lambda: self.check_for_updates(True),
        ).pack(side="right")
        self.create_button = ttk.Button(
            action_frame,
            text="Create Bootable USB",
            command=self.start_creation,
            style="Accent.TButton",
        )
        self.create_button.pack(side="left")
        ttk.Label(action_frame, textvariable=self.status).pack(side="left", padx=14)

        log_frame = ttk.LabelFrame(
            outer, text="Progress and activity log", padding=8, style="Card.TLabelframe"
        )
        log_frame.pack(fill="both", expand=True)
        self.log_box = tk.Text(
            log_frame, height=14, state="disabled", wrap="word", font=("Consolas", 9)
        )
        self.log_box.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.log_box.yview)
        scroll.pack(side="right", fill="y")
        self.log_box.configure(yscrollcommand=scroll.set)

        self.footer_label = ttk.Label(
            outer,
            text="Exboot creates installation media only. It does not activate Windows or bypass licensing.",
            font=("Segoe UI", 8),
        )
        self.footer_label.pack(anchor="w", pady=(10, 0))
        self.toggle_media_mode()

    def load_appearance_settings(self):
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            self.dark_mode.set(bool(data.get("dark_mode", False)))
            color = str(data.get("accent_color", self.accent_color))
            if color.startswith("#") and len(color) == 7:
                self.accent_color = color
        except (OSError, ValueError, TypeError):
            pass

    def save_appearance_settings(self):
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(
                json.dumps(
                    {
                        "dark_mode": self.dark_mode.get(),
                        "accent_color": self.accent_color,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError:
            self.log("Could not save appearance settings.")

    def apply_theme(self):
        dark = self.dark_mode.get()
        colors = {
            "window": "#111827" if dark else "#f3f6fb",
            "card": "#1f2937" if dark else "#ffffff",
            "text": "#f3f4f6" if dark else "#102a43",
            "muted": "#cbd5e1" if dark else "#526579",
            "input": "#111827" if dark else "#ffffff",
            "warning": "#fbbf24" if dark else "#a00000",
            "log": "#0b1220" if dark else "#ffffff",
        }
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self.configure(bg=colors["window"])
        style.configure("TFrame", background=colors["window"])
        style.configure(
            "TLabel", background=colors["window"], foreground=colors["text"]
        )
        style.configure(
            "Card.TLabelframe",
            background=colors["card"],
            foreground=colors["text"],
            padding=12,
        )
        style.configure(
            "Card.TLabelframe.Label",
            background=colors["card"],
            foreground=colors["text"],
            font=("Segoe UI", 10, "bold"),
        )
        style.configure("TButton", background=colors["card"], foreground=colors["text"])
        style.map(
            "TButton",
            background=[("active", self.accent_color)],
            foreground=[("active", "white")],
        )
        style.configure(
            "Accent.TButton",
            background=self.accent_color,
            foreground="white",
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Accent.TButton", background=[("active", self.accent_color)])
        style.configure(
            "TCheckbutton", background=colors["card"], foreground=colors["text"]
        )
        style.configure(
            "TCombobox",
            fieldbackground=colors["input"],
            background=colors["card"],
            foreground=colors["text"],
        )
        style.configure(
            "TEntry", fieldbackground=colors["input"], foreground=colors["text"]
        )
        style.configure(
            "Warning.TLabel", background=colors["window"], foreground=colors["warning"]
        )
        if hasattr(self, "log_box"):
            self.log_box.configure(
                bg=colors["log"], fg=colors["text"], insertbackground=colors["text"]
            )
        if hasattr(self, "banner"):
            self.banner.configure(bg="#111827" if dark else "#102a43")
            self.draw_banner()

    def show_appearance_settings(self):
        dialog = tk.Toplevel(self)
        dialog.title("Exboot Appearance")
        dialog.transient(self)
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Appearance", font=("Segoe UI", 15, "bold")).pack(
            anchor="w"
        )
        ttk.Label(frame, text="Customize the Exboot interface.").pack(
            anchor="w", pady=(0, 14)
        )
        ttk.Checkbutton(
            frame,
            text="Use dark mode",
            variable=self.dark_mode,
            command=self._appearance_changed,
        ).pack(anchor="w")
        color_row = ttk.Frame(frame)
        color_row.pack(fill="x", pady=(14, 0))
        ttk.Label(color_row, text="Accent color:").pack(side="left")
        swatch = tk.Label(
            color_row, width=4, height=1, bg=self.accent_color, relief="solid", bd=1
        )
        swatch.pack(side="left", padx=10)
        ttk.Button(
            color_row,
            text="Choose color…",
            command=lambda: self.choose_accent_color(swatch),
        ).pack(side="left")
        ttk.Button(frame, text="Done", command=dialog.destroy).pack(
            anchor="e", pady=(18, 0)
        )

    def _appearance_changed(self):
        self.apply_theme()
        self.save_appearance_settings()

    def choose_accent_color(self, swatch=None):
        selected = colorchooser.askcolor(
            color=self.accent_color, title="Choose Exboot accent color"
        )[1]
        if selected:
            self.accent_color = selected
            if swatch:
                swatch.configure(bg=selected)
            self.apply_theme()
            self.save_appearance_settings()

    def apply_labconfig_bypass(self, usb_drive):
        boot_wim = os.path.join(usb_drive + "\\", "sources", "boot.wim")
        if not os.path.exists(boot_wim):
            raise RuntimeError(
                "Cannot enable the bypass: sources\\boot.wim was not found on the USB."
            )
        mount_dir = tempfile.mkdtemp(prefix="exboot_bootwim_")
        mounted = False
        hive_loaded = False
        try:
            self.log("Applying TPM and Secure Boot LabConfig values to boot.wim…")
            mount_result = run_command(
                [
                    "dism.exe",
                    "/Mount-Image",
                    f"/ImageFile:{boot_wim}",
                    "/Index:2",
                    f"/MountDir:{mount_dir}",
                ],
                check=False,
            )
            if mount_result.returncode != 0:
                raise RuntimeError(mount_result.stdout + mount_result.stderr)
            mounted = True
            hive_path = os.path.join(
                mount_dir, "Windows", "System32", "Config", "SYSTEM"
            )
            load_result = run_command(
                ["reg.exe", "load", r"HKLM\ExbootLabConfig", hive_path], check=False
            )
            if load_result.returncode != 0:
                raise RuntimeError(load_result.stdout + load_result.stderr)
            hive_loaded = True
            for value in ("BypassTPMCheck", "BypassSecureBootCheck"):
                add_result = run_command(
                    [
                        "reg.exe",
                        "add",
                        r"HKLM\ExbootLabConfig\Setup\LabConfig",
                        "/v",
                        value,
                        "/t",
                        "REG_DWORD",
                        "/d",
                        "1",
                        "/f",
                    ],
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
                run_command(
                    [
                        "dism.exe",
                        "/Unmount-Image",
                        f"/MountDir:{mount_dir}",
                        "/Discard",
                    ],
                    check=False,
                )
            try:
                os.rmdir(mount_dir)
            except OSError:
                pass

    def draw_banner(self, event=None):
        width = self.banner.winfo_width()
        height = self.banner.winfo_height()
        self.banner.delete("all")
        dark = self.dark_mode.get()
        base = "#111827" if dark else "#102a43"
        secondary = "#1f2937" if dark else "#173f5f"
        self.banner.create_rectangle(0, 0, width, height, fill=base, outline="")
        self.banner.create_rectangle(
            0, height - 6, width, height, fill=self.accent_color, outline=""
        )
        self.banner.create_oval(
            width - 150, -90, width + 40, 100, fill=secondary, outline=""
        )
        self.banner.create_oval(
            width - 95, -50, width + 75, 120, fill=self.accent_color, outline=""
        )
        self.banner.create_text(
            24,
            29,
            anchor="w",
            text="ENOSX TECHNOLOGIES",
            fill=self.accent_color,
            font=("Segoe UI", 11, "bold"),
        )
        self.banner.create_text(
            24,
            59,
            anchor="w",
            text="Exboot",
            fill="white",
            font=("Segoe UI", 24, "bold"),
        )
        self.banner.create_text(
            width - 24,
            48,
            anchor="e",
            text="Windows Bootable USB Creator",
            fill="#d9eaf7",
            font=("Segoe UI", 10),
        )

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

    @staticmethod
    def select_installer_asset(release):
        """Return the exact ExbootSetup asset for a release, if it is published."""
        tag = str(release.get("tag_name", "")).strip().lstrip("vV")
        if not tag:
            return None
        expected_name = f"ExbootSetup-{tag}.exe".lower()
        for asset in release.get("assets") or []:
            name = str(asset.get("name", "")).strip()
            if name.lower() == expected_name:
                url = str(asset.get("browser_download_url", "")).strip()
                if url.startswith("https://github.com/"):
                    return asset
        return None

    @staticmethod
    def update_download_path(asset_name):
        """Return a safe temporary destination for a downloaded installer."""
        safe_name = Path(str(asset_name)).name
        if not safe_name.lower().endswith(".exe"):
            raise ValueError("The release asset is not a Windows installer.")
        update_dir = Path(tempfile.gettempdir()) / "Exboot" / "updates"
        update_dir.mkdir(parents=True, exist_ok=True)
        return update_dir / safe_name

    def periodic_update_check(self):
        self.check_for_updates(show_no_update=False, automatic=True)
        self.after(AUTO_UPDATE_INTERVAL_MS, self.periodic_update_check)

    def check_for_updates(self, show_no_update=True, automatic=False):
        if self.update_check_in_progress or getattr(
            self, "update_install_in_progress", False
        ):
            return
        self.update_check_in_progress = True
        self.status.set("Checking for updates…")
        threading.Thread(
            target=self._check_for_updates_worker,
            args=(show_no_update, automatic),
            daemon=True,
        ).start()

    def _check_for_updates_worker(self, show_no_update, automatic):
        try:
            request = urllib.request.Request(
                GITHUB_RELEASES_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "Exboot-Update-Checker",
                },
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                release = json.loads(response.read().decode("utf-8"))
            tag = release.get("tag_name", "").strip()
            release_url = release.get(
                "html_url", "https://github.com/enigmacxenosx/Exboot/releases"
            )
            notes = release.get("body") or "No release notes were provided."
            is_newer = bool(tag) and self.version_tuple(tag) > self.version_tuple(
                APP_VERSION
            )
            asset = self.select_installer_asset(release) if is_newer else None
            self.after(
                0,
                lambda: self._show_update_result(
                    is_newer,
                    tag,
                    release_url,
                    notes,
                    asset,
                    show_no_update,
                    automatic,
                ),
            )
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            OSError,
            ValueError,
        ) as exc:
            self.after(
                0, lambda err=str(exc): self._show_update_error(err, show_no_update)
            )

    def _show_update_result(
        self,
        is_newer,
        tag,
        release_url,
        notes,
        asset,
        show_no_update,
        automatic,
    ):
        self.update_check_in_progress = False
        self.status.set(f"Update available: {tag}" if is_newer else "Up to date")
        if is_newer:
            if automatic and tag == self.last_notified_update:
                self.log(
                    f"Automatic update check: {tag} is still available; notification already shown this session."
                )
                return
            self.last_notified_update = tag
            short_notes = notes[:1200] + ("…" if len(notes) > 1200 else "")
            if asset is None:
                visit_release = messagebox.askyesno(
                    "Exboot update available",
                    f"A newer release ({tag}) is available, but its matching Windows installer was not found.\n\nRelease notes:\n{short_notes}\n\nOpen the GitHub release page instead?",
                )
                if visit_release:
                    webbrowser.open(release_url)
                return
            install_now = messagebox.askyesno(
                "Exboot update available",
                f"A newer release ({tag}) is available.\n\nRelease notes:\n{short_notes}\n\nDownload and install it now? Exboot will close while the installer runs.",
            )
            if install_now:
                self.update_install_in_progress = True
                self.status.set(f"Downloading {asset.get('name', 'update')}…")
                threading.Thread(
                    target=self._download_update_worker,
                    args=(asset, tag),
                    daemon=True,
                ).start()
        elif show_no_update:
            messagebox.showinfo(
                "Exboot updates", f"You are running the latest release ({APP_VERSION})."
            )

    def _download_update_worker(self, asset, tag):
        installer_path = None
        partial_path = None
        try:
            asset_name = str(asset.get("name", "")).strip()
            download_url = str(asset.get("browser_download_url", "")).strip()
            if not download_url.startswith("https://github.com/"):
                raise ValueError("The release download URL is not trusted.")
            expected_size = int(asset.get("size") or 0)
            if expected_size > 500 * 1024 * 1024:
                raise ValueError(
                    "The release installer is larger than the allowed limit."
                )
            installer_path = self.update_download_path(asset_name)
            partial_path = installer_path.with_suffix(installer_path.suffix + ".part")
            if partial_path.exists():
                partial_path.unlink()
            request = urllib.request.Request(
                download_url,
                headers={
                    "Accept": "application/octet-stream",
                    "User-Agent": "Exboot-Update-Downloader",
                },
            )
            digest = hashlib.sha256()
            downloaded = 0
            with (
                urllib.request.urlopen(request, timeout=30) as response,
                partial_path.open("wb") as output,
            ):
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > 500 * 1024 * 1024:
                        raise ValueError(
                            "The release installer exceeded the allowed limit."
                        )
                    digest.update(chunk)
                    output.write(chunk)
            if expected_size and downloaded != expected_size:
                raise ValueError(
                    f"The downloaded installer size ({downloaded}) does not match the release size ({expected_size})."
                )
            expected_digest = str(asset.get("digest") or "").lower().strip()
            if expected_digest.startswith("sha256:"):
                expected_digest = expected_digest.split(":", 1)[1]
            if not expected_digest:
                raise ValueError(
                    "The release did not publish a usable SHA-256 checksum."
                )
            if digest.hexdigest().lower() != expected_digest:
                raise ValueError(
                    "The downloaded installer failed its SHA-256 verification."
                )
            partial_path.replace(installer_path)
            self.after(0, lambda: self._show_download_result(installer_path, tag))
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            ValueError,
        ) as exc:
            if partial_path and partial_path.exists():
                try:
                    partial_path.unlink()
                except OSError:
                    pass
            self.after(0, lambda err=str(exc): self._show_update_error(err, True))

    def _show_download_result(self, installer_path, tag):
        self.update_install_in_progress = False
        self.status.set(f"Update {tag} downloaded")
        start_now = messagebox.askyesno(
            "Exboot update ready",
            f"The {tag} installer was downloaded and verified. Start it now? Exboot will close before installation begins.",
        )
        if not start_now:
            self.log(f"Update downloaded and ready to install: {installer_path}")
            return
        try:
            subprocess.Popen([str(installer_path)], cwd=str(installer_path.parent))
        except OSError as exc:
            self._show_update_error(str(exc), True)
            return
        self.log(f"Launching update installer: {installer_path}")
        self.after(250, self.destroy)

    def _show_update_error(self, error, show_no_update):
        self.update_check_in_progress = False
        self.update_install_in_progress = False
        self.status.set("Update check unavailable")
        if show_no_update:
            messagebox.showwarning(
                "Exboot updates",
                "Exboot could not download or install the update. Please check your internet connection or visit the repository manually.",
            )
        self.log(f"Update check unavailable: {error}")

    def choose_iso(self):
        path = filedialog.askopenfilename(
            title="Select Windows ISO",
            filetypes=[("ISO images", "*.iso"), ("All files", "*.*")],
        )
        if path:
            self.iso_path.set(path)
            self.verification_signature = None
            self.checksum_status.set("Not verified")
            self.update_image_freshness(path)

    def choose_checksum_file(self):
        path = filedialog.askopenfilename(
            title="Select checksum or checksum manifest",
            filetypes=[
                ("Checksum files", "*.txt *.md5 *.sha256 *.sha256sum"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            manifest = self.parse_checksum_file(path)
            if not manifest:
                raise ValueError(
                    "No valid MD5 or SHA-256 checksum was found in the selected file."
                )
            self.checksum_manifest_path = path
            self.checksum_manifest = manifest
            iso_name = Path(self.iso_path.get().strip()).name
            expected = manifest.get(iso_name)
            if expected is None and len(manifest) == 1:
                expected = next(iter(manifest.values()))
            self.checksum_expected.set(
                expected or f"Manifest loaded: {len(manifest)} file(s)"
            )
            self.checksum_status.set("Checksum file loaded")
            self.verification_signature = None
            self.log(
                f"Loaded {len(manifest)} checksum entr(y/ies) from {Path(path).name}."
            )
        except (OSError, ValueError) as exc:
            messagebox.showerror("Checksum file error", str(exc))

    @staticmethod
    def parse_checksum_file(path):
        manifest = {}
        for line in (
            Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        ):
            fields = line.strip().split()
            digest = next(
                (
                    field.lower()
                    for field in fields
                    if re.fullmatch(r"[0-9a-fA-F]{32}|[0-9a-fA-F]{64}", field)
                ),
                None,
            )
            if not digest:
                continue
            filename = ""
            for field in reversed(fields):
                candidate = field.lstrip("*\\/")
                if candidate.lower().endswith(
                    (".iso", ".wim", ".img", ".vhd", ".vhdx")
                ):
                    filename = Path(candidate).name
                    break
            manifest[filename or f"__single_{len(manifest)}"] = digest
        return manifest

    def checksum_targets(self):
        if self.media_mode.get() == "Multi-boot USB (Ventoy)":
            return list(self.multi_iso_paths)
        iso = self.iso_path.get().strip()
        return [iso] if iso else []

    def checksum_signature(self):
        return (
            tuple(self.checksum_targets()),
            self.checksum_algorithm.get(),
            self.checksum_expected.get().strip().lower(),
            self.checksum_manifest_path,
        )

    def verify_checksums(self):
        targets = self.checksum_targets()
        if not targets or any(not Path(path).is_file() for path in targets):
            messagebox.showerror(
                "Images required",
                "Select valid ISO/image files before verifying their checksums.",
            )
            return
        algorithm = "sha256" if self.checksum_algorithm.get() == "SHA-256" else "md5"
        self.checksum_status.set("Calculating…")
        threading.Thread(
            target=self._verify_checksums_worker, args=(targets, algorithm), daemon=True
        ).start()

    def _verify_checksums_worker(self, targets, algorithm):
        try:
            calculated = {}
            for position, path in enumerate(targets, start=1):
                self.log(
                    f"Calculating {algorithm.upper()} for {Path(path).name} ({position}/{len(targets)})…"
                )
                digest = hashlib.new(algorithm)
                with open(path, "rb") as source:
                    while chunk := source.read(4 * 1024 * 1024):
                        digest.update(chunk)
                calculated[Path(path).name] = digest.hexdigest().lower()
            expected = {}
            if (
                self.media_mode.get() == "Multi-boot USB (Ventoy)"
                and self.checksum_manifest
            ):
                expected = {
                    name: value.lower()
                    for name, value in self.checksum_manifest.items()
                    if not name.startswith("__single_")
                }
            if not expected:
                typed = self.checksum_expected.get().strip().lower()
                if (
                    re.fullmatch(r"[0-9a-f]{32}|[0-9a-f]{64}", typed)
                    and len(targets) == 1
                ):
                    expected = {Path(targets[0]).name: typed}
                elif self.checksum_manifest:
                    values = list(self.checksum_manifest.values())
                    if len(values) == len(targets):
                        expected = dict(
                            zip(calculated, [value.lower() for value in values])
                        )
            if not expected:
                raise ValueError(
                    "Enter an expected checksum or load a checksum manifest before burning."
                )
            mismatches = [
                name
                for name, value in calculated.items()
                if expected.get(name) != value
            ]
            if mismatches:
                raise ValueError("Checksum mismatch: " + ", ".join(mismatches))
            signature = self.checksum_signature()
            self.after(
                0, lambda: self._verification_finished(True, signature, calculated)
            )
        except Exception as exc:
            self.after(
                0, lambda err=str(exc): self._verification_finished(False, None, err)
            )

    def _verification_finished(self, success, signature, details):
        if success:
            self.verification_signature = signature
            self.checksum_status.set("Verified")
            self.log(
                "Integrity verification passed: "
                + ", ".join(f"{name}={value}" for name, value in details.items())
            )
            messagebox.showinfo(
                "Integrity verified",
                "All selected image files match their expected checksums.",
            )
        else:
            self.verification_signature = None
            self.checksum_status.set("Verification failed")
            self.log(f"Integrity verification failed: {details}")
            messagebox.showerror("Integrity verification failed", str(details))

    def ensure_integrity_verified(self):
        if self.verification_signature != self.checksum_signature():
            messagebox.showerror(
                "Verification required",
                "Verify the selected ISO/image files successfully before creating installation media.",
            )
            return False
        return True

    def parse_benchmark_size(self):
        value = self.benchmark_size_mb.get().strip().upper()
        if value.endswith("GB"):
            return int(float(value[:-2].strip()) * 1024)
        return int(value.replace("MB", "").strip())

    def offer_benchmark(self, usb_drive):
        if not self.benchmark_after_creation.get():
            return
        size_mb = self.parse_benchmark_size()
        confirmed = messagebox.askyesno(
            "Run USB benchmark?",
            f"Run a {size_mb} MB sequential read/write benchmark on {usb_drive}?\n\n"
            "Exboot will write a temporary test file, read it back, and delete it afterward. "
            "This may take several minutes and temporarily uses USB space.",
            icon="question",
        )
        if confirmed:
            self.create_button.configure(state="disabled")
            self.status.set("Benchmarking…")
            threading.Thread(
                target=self.run_usb_benchmark, args=(usb_drive, size_mb), daemon=True
            ).start()

    def run_usb_benchmark(self, usb_drive, size_mb):
        test_path = Path(usb_drive + "\\") / f"Exboot_Benchmark_{os.getpid()}.bin"
        size_bytes = size_mb * 1024 * 1024
        chunk = b"EXBOOT-BENCHMARK-" + (b"0" * (4 * 1024 * 1024 - 17))
        try:
            usage = shutil.disk_usage(Path(usb_drive + "\\"))
            if usage.free < size_bytes + 64 * 1024 * 1024:
                raise RuntimeError(
                    f"Not enough free space for a {size_mb} MB benchmark file."
                )
            self.log(
                f"Starting USB benchmark: {size_mb} MB sequential write/read test on {usb_drive}…"
            )
            started = time.perf_counter()
            written = 0
            with test_path.open("wb", buffering=0) as target:
                while written < size_bytes:
                    amount = min(len(chunk), size_bytes - written)
                    target.write(chunk[:amount])
                    written += amount
                os.fsync(target.fileno())
            write_seconds = max(time.perf_counter() - started, 0.000001)
            started = time.perf_counter()
            read_bytes = 0
            with test_path.open("rb", buffering=0) as source:
                while source.read(4 * 1024 * 1024):
                    read_bytes += 4 * 1024 * 1024
            read_seconds = max(time.perf_counter() - started, 0.000001)
            write_speed = size_bytes / write_seconds / (1024 * 1024)
            read_speed = size_bytes / read_seconds / (1024 * 1024)
            result = {"write": write_speed, "read": read_speed, "size": size_mb}
            self.after(0, lambda: self._benchmark_finished(result))
        except Exception as exc:
            self.after(0, lambda err=str(exc): self._benchmark_failed(err))
        finally:
            try:
                if test_path.exists():
                    test_path.unlink()
            except OSError as cleanup_error:
                self.log(
                    f"WARNING: Could not remove benchmark file {test_path}: {cleanup_error}"
                )

    def _benchmark_finished(self, result):
        self.status.set("Ready")
        self.create_button.configure(state="normal")
        self.log(
            f"USB benchmark complete: write {result['write']:.1f} MiB/s; read {result['read']:.1f} MiB/s; test size {result['size']} MB."
        )
        messagebox.showinfo(
            "USB benchmark complete",
            f"Sequential write: {result['write']:.1f} MiB/s\nSequential read: {result['read']:.1f} MiB/s\nTest size: {result['size']} MB\n\nThe temporary benchmark file was removed.",
        )

    def _benchmark_failed(self, error):
        self.status.set("Ready")
        self.create_button.configure(state="normal")
        self.log(f"USB benchmark failed: {error}")
        messagebox.showerror("USB benchmark failed", error)

    @staticmethod
    def _safe_pack_forget(widget):
        if widget is None:
            return
        try:
            widget.pack_forget()
        except tk.TclError:
            pass

    def pack_before(self, widget, anchor_widget):
        if widget is None:
            return
        try:
            if anchor_widget is not None and anchor_widget.winfo_exists():
                if anchor_widget.winfo_ismapped():
                    widget.pack(fill="x", pady=(0, 12), before=anchor_widget)
                    return
            widget.pack(fill="x", pady=(0, 12))
        except tk.TclError:
            # A restored or partially-created UI may contain a stale widget
            # reference; leave that section hidden instead of crashing startup.
            pass

    def toggle_media_mode(self):
        multi = self.media_mode.get() == "Multi-boot USB (Ventoy)"
        if multi:
            self._safe_pack_forget(self.iso_frame)
            self._safe_pack_forget(self.mode_frame)
            self._safe_pack_forget(self.bypass_frame)
            self.pack_before(self.multi_frame, self.warning_label)
        else:
            self._safe_pack_forget(self.multi_frame)
            self.pack_before(self.iso_frame, self.disk_frame)
            self.pack_before(self.mode_frame, self.bypass_frame)
            self.pack_before(self.bypass_frame, self.multi_frame)

    @staticmethod
    def _read_wim_timestamp(header):
        """Convert the creation timestamp stored at WIM header offset 68 to a
        UTC datetime. The value is a Windows FILETIME (100-nanosecond intervals
        since 1601-01-01). Returns None when the value is missing or invalid."""
        if len(header) < 76:
            return None
        raw = int.from_bytes(header[68:76], "little")
        if raw == 0:
            return None
        windows_epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
        try:
            return windows_epoch + timedelta(microseconds=raw // 10)
        except (OverflowError, ValueError):
            return None

    @staticmethod
    def detect_windows_image(path):
        """Inspect a Windows installation image for build metadata (freshness).

        Reads the WIM header of install.wim/install.esd (or the file itself when
        it is a bare WIM/ESD) and returns the creation timestamp plus the header
        version. ESD files are LZMS-compressed but share the same header layout
        as WIM, so the timestamp can be read directly from the first block.
        Returns a dict with keys timestamp, wim_version, and label, or None
        when the image is not a readable Windows WIM/ESD.
        """
        path = str(path)
        suffix = Path(path).suffix.lower()
        header = None
        if suffix in (".wim", ".esd"):
            try:
                header = Path(path).read_bytes()[:4096]
            except OSError:
                return None
        elif suffix == ".iso":
            try:
                with zipfile.ZipFile(path) as archive:
                    target = next(
                        (
                            entry
                            for entry in archive.namelist()
                            if entry.lower() in ("install.wim", "install.esd")
                        ),
                        None,
                    )
                    if target:
                        with archive.open(target) as entry_file:
                            header = entry_file.read(4096)
            except (zipfile.BadZipFile, OSError):
                return None
        if header is None or len(header) < 12:
            return None
        if header[:5] != b"MSWIM":
            return None
        wim_version = (
            int.from_bytes(header[64:68], "little") if len(header) >= 68 else 0
        )
        timestamp = ExbootApp._read_wim_timestamp(header)
        return {"wim_version": wim_version, "timestamp": timestamp}

    def update_image_freshness(self, path):
        """Inspect the selected image and show its Windows build freshness.

        Windows images show the install.wim/install.esd build date and header
        version; non-Windows images stay silent so the label never shows
        placeholder text for Linux or other media."""
        self.image_freshness.set("")
        if not Path(str(path)).is_file():
            return
        meta = self.detect_windows_image(path)
        label = self.freshness_label(meta) if meta else None
        if label:
            self.image_freshness.set(f"{label}")
        else:
            classification = self.classify_image(path)
            if classification.startswith("Linux") or classification.startswith("Other"):
                self.image_freshness.set(
                    "Non-Windows image — Ventoy multi-boot supported"
                )

    def classify_image(path):
        """Return a human-readable operating-system family label for an image file.

        Windows images are recognized by the presence of install.wim/install.esd
        or sources/boot.wim inside the ISO. Everything else that Ventoy supports
        (Linux live ISOs, diagnostic images, and so on) is labeled Other/Linux.
        Detection failures return "Unknown" so classification never blocks use.
        """
        path = str(path)
        suffix = Path(path).suffix.lower()
        name = Path(path).name.lower()
        if suffix in (".wim", ".esd"):
            return "Windows (WIM/ESD)"
        if suffix in (".vhd", ".vhdx"):
            return "Windows (VHD/VHDX)"
        if suffix == ".iso":
            try:
                with zipfile.ZipFile(path) as archive:
                    entries = [entry.lower() for entry in archive.namelist()]
            except (zipfile.BadZipFile, OSError):
                return "Other / Linux"
            if any(
                entry in ("install.wim", "install.esd") or entry.startswith("sources/")
                for entry in entries
            ):
                return "Windows"
            if any(entry.startswith("casper/") for entry in entries):
                return "Linux (Ubuntu family)"
            return "Other / Linux"
        if suffix == ".img":
            return (
                "Other / Linux"
                if "raspbian" in name or "linux" in name
                else "IMG image"
            )
        return "Unknown"

    @staticmethod
    def freshness_label(meta, stale_days=730):
        """Format image metadata into a short freshness label for the UI.

        Returns None when no metadata is available so the UI can stay silent
        instead of showing placeholder text.
        """
        if not meta or not meta.get("timestamp"):
            return None
        stamp = meta["timestamp"].strftime("%Y-%m-%d")
        age = (datetime.now(timezone.utc) - meta["timestamp"]).days
        if age < 0:
            age = 0
        state = "Fresh" if age < 180 else "Dated" if age < stale_days else "Outdated"
        version = meta.get("wim_version") or 0
        return f"Built {stamp} ({state}, {age} days old) · WIM version {version}"

    def add_multi_isos(self):
        paths = filedialog.askopenfilenames(
            title="Select operating-system image files",
            filetypes=[
                (
                    "Boot images",
                    "*.iso *.wim *.esd *.img *.vhd *.vhdx",
                ),
                ("ISO images", "*.iso"),
                ("All files", "*.*"),
            ],
        )
        for path in paths:
            if path not in self.multi_iso_paths:
                self.multi_iso_paths.append(path)
        self.refresh_multi_list()
        if paths:
            families = [self.classify_image(path) for path in paths]
            summary = ", ".join(dict.fromkeys(families))
            self.log(
                f"Selected {len(self.multi_iso_paths)} multi-boot image(s): {summary}."
            )
            for path in paths:
                meta = self.detect_windows_image(path)
                label = self.freshness_label(meta)
                if label:
                    self.log(f"{Path(path).name}: {label}")
            self.verification_signature = None
            self.checksum_status.set("Not verified")

    def show_multiboot_theme_settings(self):
        dialog = tk.Toplevel(self)
        dialog.title("Multi-boot menu theme")
        dialog.transient(self)
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame, text="Ventoy / GRUB menu theme", font=("Segoe UI", 15, "bold")
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text="These settings are written to the USB only when multi-boot media is created.",
        ).pack(anchor="w", pady=(0, 14))
        title_var = tk.StringVar(value=self.theme_settings["title"])
        ttk.Label(frame, text="Menu title").pack(anchor="w")
        ttk.Entry(frame, textvariable=title_var, width=52).pack(fill="x", pady=(3, 10))
        background_var = tk.StringVar(
            value=self.theme_settings["background"] or "No background image selected"
        )
        ttk.Label(frame, textvariable=background_var).pack(anchor="w", pady=(0, 4))

        def choose_background():
            path = filedialog.askopenfilename(
                title="Choose multi-boot background image",
                filetypes=[
                    ("PNG or JPEG images", "*.png *.jpg *.jpeg"),
                    ("All files", "*.*"),
                ],
            )
            if path:
                self.theme_settings["background"] = path
                background_var.set(path)

        ttk.Button(
            frame, text="Choose background image…", command=choose_background
        ).pack(anchor="w")
        color_frame = ttk.Frame(frame)
        color_frame.pack(fill="x", pady=(14, 0))
        color_vars = {
            "background_color": ("Background color", "#061426"),
            "text_color": ("Menu text color", "#dcecff"),
            "selected_color": ("Selected item color", "#00d8ff"),
            "version_color": ("Version text color", "#7aa7d9"),
        }
        for key, (label, _) in color_vars.items():
            row = ttk.Frame(color_frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=f"{label}:", width=22).pack(side="left")
            swatch = tk.Label(
                row, width=4, bg=self.theme_settings[key], relief="solid", bd=1
            )
            swatch.pack(side="left", padx=(4, 8))

            def choose_color(setting_key=key, preview=swatch):
                selected = colorchooser.askcolor(
                    color=self.theme_settings[setting_key],
                    title=f"Choose {color_vars[setting_key][0]}",
                )[1]
                if selected:
                    self.theme_settings[setting_key] = selected
                    preview.configure(bg=selected)

            ttk.Button(row, text="Choose…", command=choose_color).pack(side="left")

        def save_and_close():
            self.theme_settings["title"] = (
                title_var.get().strip() or "Enosx Technologies Exboot"
            )
            self.log("Multi-boot theme settings updated.")
            dialog.destroy()

        ttk.Button(frame, text="Save theme settings", command=save_and_close).pack(
            anchor="e", pady=(18, 0)
        )

    def refresh_multi_list(self):
        """Rebuild the multi-boot image list so each entry shows the image path
        plus its detected operating-system family, keeping list indices aligned
        with multi_iso_paths after any add or remove."""
        self.multi_list.delete(0, "end")
        for path in self.multi_iso_paths:
            family = self.classify_image(path)
            self.multi_list.insert("end", f"{path}   [{family}]")

    def remove_multi_isos(self):
        selected = list(self.multi_list.curselection())
        for index in reversed(selected):
            del self.multi_iso_paths[index]
        self.refresh_multi_list()
        self.verification_signature = None
        self.checksum_status.set("Not verified")

    def start_multiboot_creation(self):
        if not self.ensure_integrity_verified():
            return
        if not is_admin():
            messagebox.showerror(
                "Administrator required",
                "Run Exboot as Administrator before creating multi-boot media.",
            )
            return
        index = self.disk_combo.current()
        if not self.multi_iso_paths:
            messagebox.showerror(
                "Images required", "Add at least one OS image file first."
            )
            return
        invalid = [path for path in self.multi_iso_paths if not Path(path).is_file()]
        if invalid:
            messagebox.showerror(
                "Missing image", f"These image files are unavailable:\n\n{invalid[0]}"
            )
            return
        if index < 0 or index >= len(self.disks):
            messagebox.showerror("USB required", "Select a detected USB disk first.")
            return
        disk_number = str(self.disks[index].get("Number"))
        disk_name = self.disk_combo.get()
        confirmed = messagebox.askyesno(
            "Confirm multi-boot erase",
            f"Exboot will install Ventoy and erase ALL data on:\n\n{disk_name}\n\n"
            f"The boot menu will contain {len(self.multi_iso_paths)} image(s).\n\nDo you want to continue?",
            icon="warning",
        )
        if not confirmed:
            return
        typed = simpledialog.askstring(
            "Final confirmation",
            "Type ERASE to confirm that the selected USB disk may be erased:",
        )
        if typed != "ERASE":
            self.log("Multi-boot operation cancelled: confirmation text did not match.")
            return
        self.create_button.configure(state="disabled")
        self.status.set("Working…")
        threading.Thread(
            target=self.create_multiboot_media,
            args=(list(self.multi_iso_paths), disk_number),
            daemon=True,
        ).start()

    def download_latest_ventoy(self, destination):
        request = urllib.request.Request(
            VENTOY_RELEASES_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Exboot-MultiBoot",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            release = json.loads(response.read().decode("utf-8"))
        assets = {
            item.get("name"): item.get("browser_download_url")
            for item in release.get("assets", [])
        }
        package_name = next(
            (name for name in assets if name.endswith("-windows.zip")), None
        )
        checksum_name = "sha256.txt"
        if not package_name or not assets.get(checksum_name):
            raise RuntimeError(
                "The latest official Ventoy release does not contain the expected Windows package."
            )
        package_path = Path(destination) / package_name
        checksum_path = Path(destination) / checksum_name
        self.log(f"Downloading official Ventoy {release.get('tag_name', '')} package…")
        with (
            urllib.request.urlopen(assets[package_name], timeout=120) as source,
            package_path.open("wb") as target,
        ):
            shutil.copyfileobj(source, target)
        with (
            urllib.request.urlopen(assets[checksum_name], timeout=30) as source,
            checksum_path.open("wb") as target,
        ):
            shutil.copyfileobj(source, target)
        expected = None
        for line in checksum_path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines():
            fields = line.split()
            if len(fields) >= 2 and fields[-1].strip("*") == package_name:
                expected = fields[0].lower()
                break
        if not expected:
            raise RuntimeError("Could not find the Ventoy package checksum.")
        digest = hashlib.sha256(package_path.read_bytes()).hexdigest().lower()
        if digest != expected:
            raise RuntimeError(
                "Ventoy package checksum verification failed; the download was discarded."
            )
        return package_path

    def find_ventoy_data_drive(self, disk_number):
        for _ in range(20):
            result = ps(
                f"(Get-Partition -DiskNumber {disk_number} | Get-Volume | "
                "Where-Object {$_.DriveLetter} | Sort-Object Size -Descending | "
                "Select-Object -First 1 -ExpandProperty DriveLetter)"
            )
            letters = [
                line.strip() for line in result.stdout.splitlines() if line.strip()
            ]
            if letters:
                return letters[0] + ":"
            time.sleep(2)
        raise RuntimeError(
            "Ventoy installed, but Windows did not assign a data-partition drive letter."
        )

    def create_multiboot_media(self, image_paths, disk_number):
        try:
            with tempfile.TemporaryDirectory(prefix="exboot_ventoy_") as workspace:
                package_path = self.download_latest_ventoy(workspace)
                extract_dir = Path(workspace) / "ventoy"
                with zipfile.ZipFile(package_path) as archive:
                    archive.extractall(extract_dir)
                ventoy_exe = next(extract_dir.rglob("Ventoy2Disk.exe"), None)
                if not ventoy_exe:
                    raise RuntimeError(
                        "Ventoy2Disk.exe was not found in the verified package."
                    )
                self.log(
                    f"Installing Ventoy to physical USB disk {disk_number} using GPT mode…"
                )
                result = run_command(
                    [
                        str(ventoy_exe),
                        "VTOYCLI",
                        "/I",
                        f"/PhyDrive:{disk_number}",
                        "/GPT",
                    ],
                    check=False,
                )
                if result.returncode != 0:
                    raise RuntimeError(result.stdout + result.stderr)
                usb_drive = self.find_ventoy_data_drive(disk_number)
                image_dir = Path(usb_drive + "\\") / "Exboot Images"
                image_dir.mkdir(parents=True, exist_ok=True)
                for position, source in enumerate(image_paths, start=1):
                    target = image_dir / Path(source).name
                    if target.exists():
                        target = (
                            image_dir
                            / f"{Path(source).stem}_{position}{Path(source).suffix}"
                        )
                    self.log(
                        f"Copying image {position}/{len(image_paths)}: {Path(source).name}"
                    )
                    shutil.copy2(source, target)
                self.write_ventoy_theme(usb_drive, self.theme_settings)
                self.log(
                    "Ventoy will discover the copied images and display them in the styled boot menu."
                )
            self.after(
                0,
                lambda: messagebox.showinfo(
                    "Exboot", "Multi-boot USB creation completed."
                ),
            )
            self.after(120, lambda drive=usb_drive: self.offer_benchmark(drive))
        except Exception as exc:
            self.log(f"ERROR: {exc}")
            self.after(
                0,
                lambda err=str(exc): messagebox.showerror(
                    "Exboot multi-boot failed", err
                ),
            )
        finally:
            self.after(0, lambda: self.create_button.configure(state="normal"))
            self.after(0, lambda: self.status.set("Ready"))

    def write_ventoy_theme(self, usb_drive, settings):
        ventoy_root = Path(usb_drive + "\\") / "ventoy"
        theme_dir = ventoy_root / "theme" / "exboot"
        theme_dir.mkdir(parents=True, exist_ok=True)
        background_name = ""
        background = settings.get("background")
        if background and Path(background).is_file():
            suffix = Path(background).suffix.lower()
            if suffix not in (".png", ".jpg", ".jpeg"):
                raise RuntimeError(
                    "The multi-boot background must be a PNG or JPEG image."
                )
            background_name = "background" + suffix
            shutil.copy2(background, theme_dir / background_name)
        theme_lines = [
            f'desktop-color: "{settings.get("background_color", "#061426")}"',
            f'title-text: "{settings.get("title") or "Enosx Technologies Exboot"}"',
            'title-font: "DejaVu Sans Bold 28"',
            f'title-color: "{settings.get("selected_color", "#00d8ff")}"',
            'title-position: "center"',
            "+ boot_menu {",
            "    left = 18%",
            "    top = 27%",
            "    width = 64%",
            "    height = 55%",
            '    item_font = "DejaVu Sans 18"',
            f'    item_color = "{settings.get("text_color", "#dcecff")}"',
            f'    selected_item_color = "{settings.get("selected_color", "#00d8ff")}"',
            "    item_height = 38",
            "    item_padding = 10",
            "    item_spacing = 6",
            "}",
            "+ label {",
            '    id = "ventoy_version"',
            "    left = 3%",
            "    top = 94%",
            "    width = 94%",
            "    height = 30",
            '    text = "${VTLANG}"',
            '    align = "left"',
            f'    color = "{settings.get("version_color", "#7aa7d9")}"',
            '    font = "DejaVu Sans 12"',
            "}",
        ]
        if background_name:
            theme_lines.insert(0, f'desktop-image: "{background_name}"')
        (theme_dir / "theme.txt").write_text(
            "\n".join(theme_lines) + "\n", encoding="utf-8"
        )
        ventoy_json = {"theme": {"file": "/ventoy/theme/exboot/theme.txt"}}
        (ventoy_root / "ventoy.json").write_text(
            json.dumps(ventoy_json, indent=2), encoding="utf-8"
        )
        self.log("Custom GRUB/Ventoy theme configuration written to the USB.")

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
                self.log(
                    "No USB disks detected. Connect a USB drive and click Refresh."
                )
        except Exception as exc:
            self.log(f"Could not enumerate USB disks: {exc}")

    def start_creation(self):
        if self.media_mode.get() == "Multi-boot USB (Ventoy)":
            self.start_multiboot_creation()
            return
        if not self.ensure_integrity_verified():
            return
        if not is_admin():
            messagebox.showerror(
                "Administrator required",
                "Run Exboot as Administrator before creating USB media.",
            )
            return
        iso = self.iso_path.get().strip()
        index = self.disk_combo.current()
        if not iso or not Path(iso).is_file():
            messagebox.showerror(
                "ISO required", "Select a valid Windows ISO file first."
            )
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
            "Final confirmation",
            "Type ERASE to confirm that the selected USB disk may be erased:",
        )
        if typed != "ERASE":
            self.log("Operation cancelled: confirmation text did not match.")
            return
        self.create_button.configure(state="disabled")
        self.status.set("Working…")
        threading.Thread(
            target=self.create_media,
            args=(
                iso,
                disk_number,
                self.partition_mode.get(),
                self.bypass_checks.get(),
            ),
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
            if not os.path.exists(
                os.path.join(iso_drive + "\\", "sources", "install.wim")
            ) and not os.path.exists(
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
            with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", delete=False, encoding="ascii"
            ) as handle:
                handle.write(script)
                diskpart_script = handle.name
            try:
                self.log(
                    f"Formatting Disk {disk_number} as {partition_scheme.upper()}/{filesystem.upper()} for {mode}…"
                )
                result = run_command(
                    ["diskpart.exe", "/s", diskpart_script], check=False
                )
                if result.returncode != 0:
                    raise RuntimeError(result.stdout + result.stderr)
            finally:
                os.unlink(diskpart_script)

            usb_result = ps("(Get-Volume -FileSystemLabel WIN11).DriveLetter")
            usb_drive = usb_result.stdout.strip().splitlines()[0] + ":"
            self.log(f"USB assigned as {usb_drive}")
            self.log("Copying Windows files…")
            copy_result = run_command(
                [
                    "robocopy.exe",
                    iso_drive + "\\",
                    usb_drive + "\\",
                    "/E",
                    "/R:2",
                    "/W:2",
                    "/XF",
                    "install.wim",
                    "install.esd",
                ],
                check=False,
            )
            if copy_result.returncode >= 8:
                raise RuntimeError(copy_result.stdout + copy_result.stderr)

            wim = iso_drive + "\\sources\\install.wim"
            if os.path.exists(wim):
                self.log("Splitting install.wim for FAT32 compatibility…")
                result = run_command(
                    [
                        "dism.exe",
                        "/Split-Image",
                        f"/ImageFile:{wim}",
                        f"/SWMFile:{usb_drive}\\sources\\install.swm",
                        "/FileSize:3800",
                    ],
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
                active_script = (
                    f"select disk {disk_number}\nselect partition 1\nactive\nexit\n"
                )
                with tempfile.NamedTemporaryFile(
                    "w", suffix=".txt", delete=False, encoding="ascii"
                ) as handle:
                    handle.write(active_script)
                    active_path = handle.name
                try:
                    run_command(["diskpart.exe", "/s", active_path], check=False)
                finally:
                    os.unlink(active_path)
            self.log(f"Completed successfully using {mode}.")
            self.after(
                0,
                lambda: messagebox.showinfo(
                    "Exboot", "Bootable Windows USB creation completed."
                ),
            )
            self.after(120, lambda drive=usb_drive: self.offer_benchmark(drive))
        except Exception as exc:
            self.log(f"ERROR: {exc}")
            self.after(
                0, lambda err=str(exc): messagebox.showerror("Exboot failed", err)
            )
        finally:
            if mounted:
                ps(f"Dismount-DiskImage -ImagePath {json.dumps(iso)}")
            self.after(0, lambda: self.create_button.configure(state="normal"))
            self.after(0, lambda: self.status.set("Ready"))


if __name__ == "__main__":
    if "--smoke-test" in sys.argv:
        # Headless CI smoke test: construct the application UI to confirm all
        # widgets render without exceptions, then close immediately and exit.
        app = ExbootApp()
        app.update_idletasks()
        app.after(0, app.destroy)
        app.mainloop()
        raise SystemExit(0)
    if sys.platform != "win32":
        print("Exboot must run on Windows.")
        raise SystemExit(1)
    app = ExbootApp()
    app.mainloop()
