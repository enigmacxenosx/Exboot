import ctypes
import json
import os
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

APP_NAME = "Exboot"


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
        self.geometry("760x560")
        self.minsize(680, 500)
        self.resizable(True, True)
        self.disks = []
        self.iso_path = tk.StringVar()
        self.selected_disk = tk.StringVar()
        self.status = tk.StringVar(value="Ready")
        self.build_ui()
        self.refresh_disks()

    def build_ui(self):
        outer = ttk.Frame(self, padding=18)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Exboot", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="Create Windows installation media from a genuine ISO.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 16))

        iso_frame = ttk.LabelFrame(outer, text="1. Windows ISO", padding=12)
        iso_frame.pack(fill="x", pady=(0, 12))
        ttk.Entry(iso_frame, textvariable=self.iso_path).pack(side="left", fill="x", expand=True)
        ttk.Button(iso_frame, text="Browse…", command=self.choose_iso).pack(side="left", padx=(8, 0))

        disk_frame = ttk.LabelFrame(outer, text="2. Target USB drive", padding=12)
        disk_frame.pack(fill="x", pady=(0, 12))
        self.disk_combo = ttk.Combobox(
            disk_frame, textvariable=self.selected_disk, state="readonly"
        )
        self.disk_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(disk_frame, text="Refresh", command=self.refresh_disks).pack(side="left", padx=(8, 0))

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
        self.create_button = ttk.Button(
            action_frame, text="Create Bootable USB", command=self.start_creation
        )
        self.create_button.pack(side="left")
        ttk.Label(action_frame, textvariable=self.status).pack(side="left", padx=14)

        log_frame = ttk.LabelFrame(outer, text="Progress", padding=8)
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

    def log(self, text):
        def append():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", text.rstrip() + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, append)

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
            f"Exboot will erase ALL data on:\n\n{disk_name}\n\nDo you want to continue?",
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
        threading.Thread(target=self.create_media, args=(iso, disk_number), daemon=True).start()

    def create_media(self, iso, disk_number):
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

            script = "\n".join(
                [
                    f"select disk {disk_number}",
                    "clean",
                    "convert gpt",
                    "create partition primary",
                    "format fs=fat32 quick label=WIN11",
                    "assign",
                    "exit",
                ]
            )
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="ascii") as handle:
                handle.write(script)
                diskpart_script = handle.name
            try:
                self.log(f"Formatting Disk {disk_number} as GPT/FAT32…")
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

            self.log("Marking the USB partition active where supported…")
            active_script = f"select disk {disk_number}\nselect partition 1\nactive\nexit\n"
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="ascii") as handle:
                handle.write(active_script)
                active_path = handle.name
            try:
                run_command(["diskpart.exe", "/s", active_path], check=False)
            finally:
                os.unlink(active_path)
            self.log("Completed successfully. You can boot the target computer from the USB.")
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
