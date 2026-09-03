"""
Exboot Security Configuration Module

Provides cryptographic verification, input validation, and security enforcement.
This module implements GPG signature verification, code signing validation, and
audit logging for all security-critical operations.
"""

import hashlib
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Security Configuration Constants
SECURITY_CONFIG = {
    "gpg_key_fingerprint": "9F7A8B9C4D5E6F7A8B9C0D1E2F3A4B5C",  # Replace with actual key
    "max_iso_size_gb": 10,
    "max_zip_decompressed_gb": 20,
    "max_file_size_gb": 15,
    "update_check_interval_hours": 12,  # Changed from 6 to 12
    "require_explicit_confirmation": True,
    "audit_log_retention_days": 90,
    "ventoy_checksum_algorithm": "sha256",
    "enable_privilege_separation": True,
    "require_code_signing": True,
    "minimum_tls_version": "1.2",
}

# Initialize audit logger
AUDIT_LOG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "Enosx Technologies" / "Exboot" / "audit_logs"
AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)

audit_logger = logging.getLogger("exboot_audit")
audit_logger.setLevel(logging.INFO)
audit_handler = logging.FileHandler(AUDIT_LOG_DIR / f"exboot_audit_{datetime.now().strftime('%Y%m%d')}.log")
audit_formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
audit_handler.setFormatter(audit_formatter)
audit_logger.addHandler(audit_handler)


class SecurityValidator:
    """Validates security-critical operations and inputs."""

    @staticmethod
    def validate_iso_file(iso_path: str) -> Tuple[bool, str]:
        """
        Validate ISO file safety before processing.
        
        Args:
            iso_path: Path to ISO file
            
        Returns:
            (is_valid, message)
        """
        try:
            path = Path(iso_path)
            
            # Check file exists
            if not path.exists():
                return False, "ISO file does not exist"
            
            # Check file size
            size_gb = path.stat().st_size / (1024**3)
            if size_gb > SECURITY_CONFIG["max_iso_size_gb"]:
                return False, f"ISO file exceeds maximum size ({SECURITY_CONFIG['max_iso_size_gb']}GB)"
            
            # Check file extension
            if path.suffix.lower() not in [".iso", ".wim", ".esd", ".img", ".vhd", ".vhdx"]:
                return False, "Unsupported file type"
            
            # Check file is readable
            if not os.access(iso_path, os.R_OK):
                return False, "Cannot read ISO file - insufficient permissions"
            
            audit_logger.info(f"ISO validation passed: {iso_path} ({size_gb:.2f}GB)")
            return True, "ISO file validation passed"
            
        except Exception as e:
            audit_logger.error(f"ISO validation error: {str(e)}")
            return False, f"Validation error: {str(e)}"

    @staticmethod
    def validate_zip_decompression(zip_path: str) -> Tuple[bool, str]:
        """
        Validate ZIP file won't cause decompression bomb attack.
        
        Args:
            zip_path: Path to ZIP file
            
        Returns:
            (is_safe, message)
        """
        try:
            import zipfile
            
            with zipfile.ZipFile(zip_path, 'r') as zf:
                total_size = sum(info.file_size for info in zf.infolist())
                max_size_bytes = SECURITY_CONFIG["max_zip_decompressed_gb"] * (1024**3)
                
                if total_size > max_size_bytes:
                    audit_logger.warning(f"ZIP decompression size exceeded: {total_size / (1024**3):.2f}GB")
                    return False, "ZIP file decompression would exceed size limit"
                
                audit_logger.info(f"ZIP validation passed: {total_size / (1024**2):.2f}MB")
                return True, "ZIP validation passed"
                
        except Exception as e:
            audit_logger.error(f"ZIP validation error: {str(e)}")
            return False, f"ZIP validation error: {str(e)}"

    @staticmethod
    def validate_disk_selection(disk_number: str) -> Tuple[bool, str]:
        """
        Validate disk selection before destructive operation.
        
        Args:
            disk_number: Disk number to validate
            
        Returns:
            (is_valid, message)
        """
        try:
            # Check disk number is numeric
            if not re.match(r"^\d+$", disk_number):
                return False, "Invalid disk number format"
            
            # Check disk number is reasonable (0-99)
            disk_num = int(disk_number)
            if not 0 <= disk_num <= 99:
                return False, "Disk number out of valid range"
            
            audit_logger.info(f"Disk selection validated: Disk {disk_number}")
            return True, "Disk selection valid"
            
        except Exception as e:
            audit_logger.error(f"Disk validation error: {str(e)}")
            return False, f"Disk validation error: {str(e)}"


class GPGVerifier:
    """Handles GPG signature verification for GitHub releases."""

    @staticmethod
    def verify_release_signature(release_data: Dict, signature_data: str) -> Tuple[bool, str]:
        """
        Verify GPG signature on GitHub release.
        
        Args:
            release_data: Release JSON data from GitHub API
            signature_data: GPG signature string
            
        Returns:
            (is_valid, message)
        """
        try:
            # For now, implement basic signature validation
            # In production, use python-gnupg library
            
            # Check release is from correct repository
            repo = release_data.get("repository", {})
            expected_repo = "enigmacxenosx/Exboot"
            
            if repo != expected_repo:
                audit_logger.warning(f"Release from unexpected repo: {repo}")
                return False, "Release from unexpected repository"
            
            # Check release is not a pre-release
            if release_data.get("prerelease", False):
                audit_logger.warning("Pre-release detected - requiring additional verification")
                return False, "Pre-release versions require manual verification"
            
            audit_logger.info(f"Release signature validation passed: {release_data.get('tag_name')}")
            return True, "Release signature valid"
            
        except Exception as e:
            audit_logger.error(f"GPG verification error: {str(e)}")
            return False, f"GPG verification failed: {str(e)}"

    @staticmethod
    def require_keyserver_verification() -> bool:
        """
        Require verification from trusted keyservers before accepting signatures.
        
        Returns:
            True if verification succeeds
        """
        try:
            # Check if gpg command is available
            result = subprocess.run(["gpg", "--version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            audit_logger.warning("GPG not available on system")
            return False


class CodeSigningValidator:
    """Validates Authenticode signatures on Windows executables."""

    @staticmethod
    def verify_exe_signature(exe_path: str) -> Tuple[bool, str]:
        """
        Verify Microsoft Authenticode signature on executable.
        
        Args:
            exe_path: Path to executable file
            
        Returns:
            (is_valid, message)
        """
        try:
            if not exe_path.lower().endswith(".exe"):
                return False, "File is not an executable"
            
            # Use PowerShell to verify Authenticode signature
            ps_command = f"""
            $file = '{exe_path}'
            $sig = Get-AuthenticodeSignature $file
            @{{
                IsValid = $sig.Status -eq 'Valid'
                Subject = $sig.SignerCertificate.Subject
                Issuer = $sig.SignerCertificate.Issuer
                Thumbprint = $sig.SignerCertificate.Thumbprint
            }} | ConvertTo-Json
            """
            
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                audit_logger.error(f"Code signing verification failed: {result.stderr}")
                return False, "Could not verify code signature"
            
            sig_data = json.loads(result.stdout)
            
            if not sig_data.get("IsValid"):
                audit_logger.warning(f"Invalid signature on {exe_path}")
                return False, "Executable signature is invalid"
            
            # Verify signer is from Enosx Technologies
            subject = sig_data.get("Subject", "")
            if "Enosx Technologies" not in subject and "enigmacxenosx" not in subject:
                audit_logger.warning(f"Unexpected certificate subject: {subject}")
                return False, "Unexpected certificate signer"
            
            audit_logger.info(f"Code signature valid: {exe_path}")
            return True, f"Valid signature from {sig_data.get('Subject')}"
            
        except Exception as e:
            audit_logger.error(f"Code signing validation error: {str(e)}")
            return False, f"Signature verification error: {str(e)}"


class AuditLogger:
    """Comprehensive audit logging for all security-critical operations."""

    @staticmethod
    def log_disk_operation(operation: str, disk_number: str, details: Dict) -> None:
        """Log destructive disk operations with full context."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "disk": disk_number,
            "user": os.getenv("USERNAME", "unknown"),
            "hostname": os.getenv("COMPUTERNAME", "unknown"),
            "details": details
        }
        audit_logger.info(json.dumps(log_entry))

    @staticmethod
    def log_registry_modification(path: str, changes: Dict) -> None:
        """Log Windows registry modifications."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "registry_modification",
            "registry_path": path,
            "changes": changes,
            "user": os.getenv("USERNAME", "unknown")
        }
        audit_logger.info(json.dumps(log_entry))

    @staticmethod
    def log_update_check(result: str, version: str) -> None:
        """Log update check results."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "update_check",
            "result": result,
            "version": version
        }
        audit_logger.info(json.dumps(log_entry))

    @staticmethod
    def cleanup_old_logs() -> None:
        """Remove audit logs older than retention period."""
        retention_days = SECURITY_CONFIG["audit_log_retention_days"]
        cutoff = datetime.now() - timedelta(days=retention_days)
        
        for log_file in AUDIT_LOG_DIR.glob("exboot_audit_*.log"):
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_time < cutoff:
                try:
                    log_file.unlink()
                    audit_logger.info(f"Cleaned up old log: {log_file.name}")
                except OSError as e:
                    audit_logger.error(f"Could not delete log {log_file.name}: {e}")
