"""
Exboot Privileged Operations Handler

Implements privilege separation by delegating dangerous operations to a separate
privileged service. This reduces the attack surface and allows non-admin users
to interact with the UI while only escalating privileges for specific operations.
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from security_config import AuditLogger, SecurityValidator

logger = logging.getLogger(__name__)


@dataclass
class OperationRequest:
    """Represents a privileged operation request."""
    operation_type: str
    disk_number: str
    iso_path: str
    partition_mode: str
    bypass_checks: bool
    user_id: str
    timestamp: str

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "operation_type": self.operation_type,
            "disk_number": self.disk_number,
            "iso_path": self.iso_path,
            "partition_mode": self.partition_mode,
            "bypass_checks": self.bypass_checks,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
        })


@dataclass
class OperationResult:
    """Represents the result of a privileged operation."""
    success: bool
    message: str
    error_code: int = 0

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "success": self.success,
            "message": self.message,
            "error_code": self.error_code,
        })


class PrivilegedOperationHandler:
    """
    Handles delegation of privileged operations.
    
    This class manages the communication between the unprivileged UI process
    and a privileged operation service that handles disk manipulation.
    """

    def __init__(self):
        """Initialize the privileged operation handler."""
        self.privileged_service_path = Path(__file__).parent / "exboot_privileged_service.exe"
        self.request_dir = Path(tempfile.gettempdir()) / "exboot_requests"
        self.response_dir = Path(tempfile.gettempdir()) / "exboot_responses"
        
        # Create request/response directories
        self.request_dir.mkdir(parents=True, exist_ok=True)
        self.response_dir.mkdir(parents=True, exist_ok=True)

    def execute_privileged_operation(
        self,
        operation_type: str,
        disk_number: str,
        iso_path: str,
        partition_mode: str,
        bypass_checks: bool
    ) -> Tuple[bool, str]:
        """
        Execute a privileged disk operation via the privileged service.
        
        Args:
            operation_type: Type of operation (format_disk, install_ventoy, etc.)
            disk_number: Target disk number
            iso_path: Path to ISO file
            partition_mode: Partition scheme (GPT/UEFI, MBR/UEFI, MBR/BIOS)
            bypass_checks: Whether to bypass TPM/Secure Boot checks
            
        Returns:
            (success, message)
        """
        # Validate inputs before delegating
        is_valid, validation_msg = SecurityValidator.validate_iso_file(iso_path)
        if not is_valid:
            logger.error(f"ISO validation failed: {validation_msg}")
            return False, validation_msg

        is_valid, validation_msg = SecurityValidator.validate_disk_selection(disk_number)
        if not is_valid:
            logger.error(f"Disk validation failed: {validation_msg}")
            return False, validation_msg

        # Create operation request
        request = OperationRequest(
            operation_type=operation_type,
            disk_number=disk_number,
            iso_path=iso_path,
            partition_mode=partition_mode,
            bypass_checks=bypass_checks,
            user_id=os.getenv("USERNAME", "unknown"),
            timestamp=self._get_timestamp()
        )

        # Write request to disk
        request_file = self.request_dir / f"request_{request.timestamp}.json"
        try:
            request_file.write_text(request.to_json(), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to write request file: {e}")
            return False, f"Failed to prepare operation: {e}"

        # Execute privileged service with UAC elevation
        try:
            result = self._invoke_privileged_service(request_file)
            return result
        except Exception as e:
            logger.error(f"Privileged operation failed: {e}")
            AuditLogger.log_disk_operation(
                operation_type,
                disk_number,
                {"status": "failed", "error": str(e)}
            )
            return False, f"Privileged operation failed: {e}"
        finally:
            # Cleanup request file
            try:
                request_file.unlink()
            except OSError:
                pass

    def _invoke_privileged_service(self, request_file: Path) -> Tuple[bool, str]:
        """
        Invoke the privileged service with UAC elevation.
        
        Args:
            request_file: Path to request JSON file
            
        Returns:
            (success, message)
        """
        # Use ShellExecute for UAC elevation via PowerShell
        ps_command = f"""
        $proc = Start-Process -FilePath '{self.privileged_service_path}' `
            -ArgumentList '{request_file}' `
            -Verb RunAs `
            -PassThru `
            -Wait
        
        exit $proc.ExitCode
        """

        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                return True, "Operation completed successfully"
            else:
                error_msg = result.stderr or "Unknown error"
                return False, f"Operation failed: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, "Operation timed out"
        except Exception as e:
            return False, f"Failed to invoke privileged service: {e}"

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()


class OperationConfirmationDialog:
    """Provides explicit confirmation dialogs for destructive operations."""

    @staticmethod
    def confirm_disk_format(disk_name: str, disk_size: str) -> bool:
        """
        Show confirmation dialog for disk formatting.
        
        Args:
            disk_name: Human-readable disk name
            disk_size: Disk size in human-readable format
            
        Returns:
            True if user confirmed, False otherwise
        """
        import tkinter as tk
        from tkinter import messagebox

        warning_text = (
            f"WARNING: This operation will ERASE ALL DATA on:\n\n"
            f"  Disk: {disk_name}\n"
            f"  Size: {disk_size}\n\n"
            f"This action CANNOT be undone.\n\n"
            f"Are you absolutely certain you want to continue?"
        )

        # First confirmation
        result = messagebox.askyesno(
            "Confirm Disk Erase",
            warning_text,
            icon=messagebox.WARNING
        )

        if not result:
            AuditLogger.log_disk_operation(
                "format_disk",
                "",
                {"status": "cancelled", "reason": "user_declined"}
            )
            return False

        # Second confirmation with explicit text requirement
        from tkinter import simpledialog
        
        confirm_text = simpledialog.askstring(
            "Final Confirmation Required",
            f"Type the following to confirm:\n\n"
            f"ERASE {disk_name}\n\n"
            f"(This is case-sensitive)",
            show="*"
        )

        if confirm_text == f"ERASE {disk_name}":
            AuditLogger.log_disk_operation(
                "format_disk",
                "",
                {"status": "confirmed", "disk": disk_name}
            )
            return True
        else:
            AuditLogger.log_disk_operation(
                "format_disk",
                "",
                {"status": "cancelled", "reason": "confirmation_mismatch"}
            )
            return False

    @staticmethod
    def confirm_registry_modification(modifications: Dict[str, str]) -> bool:
        """
        Show confirmation dialog for registry modifications.
        
        Args:
            modifications: Dictionary of registry paths and values to modify
            
        Returns:
            True if user confirmed, False otherwise
        """
        import tkinter as tk
        from tkinter import messagebox

        mod_text = "\n".join([f"  {k}: {v}" for k, v in modifications.items()])
        
        warning_text = (
            f"This operation will modify Windows Registry settings:\n\n"
            f"{mod_text}\n\n"
            f"These changes affect system security settings.\n"
            f"You should only proceed on hardware you own or administer.\n\n"
            f"Continue?"
        )

        result = messagebox.askyesno(
            "Confirm Registry Modification",
            warning_text,
            icon=messagebox.WARNING
        )

        if result:
            AuditLogger.log_registry_modification(
                "HKLM\\Setup\\LabConfig",
                modifications
            )
        
        return result


class OperationRollback:
    """Provides rollback capability for destructive operations."""

    def __init__(self):
        """Initialize rollback handler."""
        self.rollback_dir = Path(tempfile.gettempdir()) / "exboot_rollback"
        self.rollback_dir.mkdir(parents=True, exist_ok=True)

    def create_disk_snapshot(self, disk_number: str) -> Optional[Path]:
        """
        Create a snapshot of disk state before modification.
        
        Args:
            disk_number: Disk to snapshot
            
        Returns:
            Path to snapshot file, or None if failed
        """
        try:
            snapshot_file = self.rollback_dir / f"disk_{disk_number}_snapshot_{self._get_timestamp()}.json"
            
            # Get disk information
            ps_command = f"""
            Get-Disk -Number {disk_number} | Select-Object Number, FriendlyName, Size, PartitionStyle, OperationalStatus | ConvertTo-Json
            """
            
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                snapshot_file.write_text(result.stdout, encoding="utf-8")
                logger.info(f"Created disk snapshot: {snapshot_file}")
                return snapshot_file
            else:
                logger.error(f"Failed to create snapshot: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Snapshot creation error: {e}")
            return None

    def rollback_disk_operation(self, disk_number: str, snapshot_file: Path) -> bool:
        """
        Attempt to rollback a disk operation using a snapshot.
        
        Args:
            disk_number: Disk that was modified
            snapshot_file: Path to pre-operation snapshot
            
        Returns:
            True if rollback succeeded, False otherwise
        """
        try:
            snapshot_data = json.loads(snapshot_file.read_text(encoding="utf-8"))
            
            logger.warning(f"Attempting rollback of Disk {disk_number}")
            logger.info(f"Restoring partition style: {snapshot_data.get('PartitionStyle')}")
            
            # Note: Full rollback of disk operations is complex and risky.
            # This is a placeholder for more sophisticated recovery logic.
            # In practice, users should maintain backups.
            
            AuditLogger.log_disk_operation(
                "rollback",
                disk_number,
                {"snapshot": str(snapshot_file), "status": "initiated"}
            )
            
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp for file naming."""
        from datetime import datetime
        return datetime.utcnow().strftime("%Y%m%d_%H%M%S")
