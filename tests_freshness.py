"""Unit tests for image classification and freshness detection."""
import struct
import zipfile
from datetime import datetime, timezone

from exboot import ExbootApp


def make_wim_header(build_date: datetime, wim_version: int = 13) -> bytes:
    """Craft a minimal MSWIM header with the given FILETIME timestamp."""
    header = bytearray(4096)
    header[0:5] = b"MSWIM"
    # wim_version at offset 64 (uint32)
    header[64:68] = struct.pack("<I", wim_version)
    # FILETIME at offset 68: 100-ns intervals since 1601-01-01
    delta = build_date - datetime(1601, 1, 1, tzinfo=timezone.utc)
    raw = int(delta.total_seconds() * 10_000_000)
    header[68:76] = struct.pack("<Q", raw)
    return bytes(header)


def iso_with(name: str, content: bytes) -> str:
    import tempfile
    from pathlib import Path

    tmp = tempfile.mktemp(suffix=".iso")
    with zipfile.ZipFile(tmp, "w") as archive:
        archive.writestr(name, content)
    return tmp


def test_classification_linux_iso():
    path = iso_with("casper/filesystem.squashfs", b"x" * 100)
    assert ExbootApp.classify_image(path) == "Linux (Ubuntu family)", ExbootApp.classify_image(path)


def test_classification_other_iso():
    path = iso_with("some/random/file", b"x" * 100)
    assert ExbootApp.classify_image(path) == "Other / Linux", ExbootApp.classify_image(path)


def test_classification_vhd():
    assert ExbootApp.classify_image("/tmp/disk.vhd") == "Windows (VHD/VHDX)"
    assert ExbootApp.classify_image("/tmp/disk.vhdx") == "Windows (VHD/VHDX)"


def test_classification_bare_wim():
    import tempfile

    tmp = tempfile.mktemp(suffix=".wim")
    Path(tmp).write_bytes(make_wim_header(datetime(2025, 6, 1, tzinfo=timezone.utc)))
    assert ExbootApp.classify_image(tmp) == "Windows (WIM/ESD)"


def test_classification_esd():
    import tempfile
    from pathlib import Path

    tmp = tempfile.mktemp(suffix=".esd")
    Path(tmp).write_bytes(make_wim_header(datetime(2024, 1, 1, tzinfo=timezone.utc)))
    assert ExbootApp.classify_image(tmp) == "Windows (WIM/ESD)"


def test_classification_unknown_extension():
    assert ExbootApp.classify_image("/tmp/data.xyz") == "Unknown"


def test_freshness_recent_build():
    path = iso_with("install.wim", make_wim_header(datetime(2026, 7, 1, tzinfo=timezone.utc)))
    meta = ExbootApp.detect_windows_image(path)
    assert meta is not None
    assert meta["wim_version"] == 13
    assert meta["timestamp"].year == 2026
    label = ExbootApp.freshness_label(meta)
    assert label is not None
    assert "Fresh" in label
    print("freshness label:", label)


def test_freshness_old_build():
    path = iso_with("install.wim", make_wim_header(datetime(2020, 3, 1, tzinfo=timezone.utc)))
    meta = ExbootApp.detect_windows_image(path)
    assert meta is not None
    label = ExbootApp.freshness_label(meta)
    assert label is not None
    assert "Outdated" in label
    print("freshness label:", label)


def test_freshness_esd_iso():
    path = iso_with("install.esd", make_wim_header(datetime(2025, 11, 15, tzinfo=timezone.utc)))
    meta = ExbootApp.detect_windows_image(path)
    assert meta is not None
    label = ExbootApp.freshness_label(meta)
    assert label is not None
    print("freshness label:", label)


def test_freshness_non_windows_iso():
    path = iso_with("casper/filesystem.squashfs", b"x" * 100)
    meta = ExbootApp.detect_windows_image(path)
    assert meta is None


def test_freshness_bad_iso():
    import tempfile

    path = tempfile.mktemp(suffix=".iso")
    Path(path).write_text("not a zip archive at all")
    meta = ExbootApp.detect_windows_image(path)
    assert meta is None


def test_read_wim_timestamp_invalid():
    assert ExbootApp._read_wim_timestamp(b"\x00" * 76) is None
    assert ExbootApp._read_wim_timestamp(b"\x00" * 10) is None


def test_select_installer_asset():
    release = {
        "tag_name": "v0.4.0",
        "assets": [
            {
                "name": "ExbootSetup-0.4.0.exe",
                "browser_download_url": (
                    "https://github.com/enigmacxenosx/Exboot/releases/"
                    "download/v0.4.0/ExbootSetup-0.4.0.exe"
                ),
            },
            {
                "name": "ExbootSetup-0.3.1.exe",
                "browser_download_url": "https://example.com/old.exe",
            },
        ],
    }
    asset = ExbootApp.select_installer_asset(release)
    assert asset is not None
    assert asset["name"] == "ExbootSetup-0.4.0.exe"


def test_select_installer_asset_rejects_untrusted_url():
    release = {
        "tag_name": "v0.4.0",
        "assets": [
            {
                "name": "ExbootSetup-0.4.0.exe",
                "browser_download_url": "https://example.com/ExbootSetup-0.4.0.exe",
            }
        ],
    }
    assert ExbootApp.select_installer_asset(release) is None


if __name__ == "__main__":
    from pathlib import Path

    tests = [
        test_classification_linux_iso,
        test_classification_other_iso,
        test_classification_vhd,
        test_classification_bare_wim,
        test_classification_esd,
        test_classification_unknown_extension,
        test_freshness_recent_build,
        test_freshness_old_build,
        test_freshness_esd_iso,
        test_freshness_non_windows_iso,
        test_freshness_bad_iso,
        test_read_wim_timestamp_invalid,
        test_select_installer_asset,
        test_select_installer_asset_rejects_untrusted_url,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL  {test.__name__}: {exc}")
    raise SystemExit(1 if failed else 0)
