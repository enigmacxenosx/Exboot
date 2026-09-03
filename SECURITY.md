# Exboot Security Policy and Improvements

## Overview

Exboot v0.3.8+ includes comprehensive security enhancements to address critical vulnerabilities identified in the codebase. This document outlines the security measures, recommendations for users, and best practices.

## Security Enhancements Implemented

### 1. GPG Signature Verification ✅
**Status: Implemented**

All GitHub releases are now verified using GPG signatures before download and installation.

- **Module**: `security_config.py` - `GPGVerifier` class
- **Features**:
  - Signature verification against trusted keyservers
  - Pre-release rejection (requires manual review)
  - Repository source pinning
- **Usage**:
  ```python
  from security_config import GPGVerifier
  is_valid, msg = GPGVerifier.verify_release_signature(release_data, signature)
  ```

### 2. Code Signing (Authenticode) Verification ✅
**Status: Implemented**

All executables are cryptographically signed and verified before execution.

- **Module**: `security_config.py` - `CodeSigningValidator` class
- **Features**:
  - Microsoft Authenticode signature verification
  - Certificate subject validation
  - Certificate chain verification
- **Usage**:
  ```python
  from security_config import CodeSigningValidator
  is_valid, msg = CodeSigningValidator.verify_exe_signature(exe_path)
  ```

### 3. Input Validation ✅
**Status: Implemented**

Comprehensive validation of all user inputs before processing.

- **Module**: `security_config.py` - `SecurityValidator` class
- **Features**:
  - ISO file size validation (max 10GB)
  - ZIP decompression bomb protection (max 20GB decompressed)
  - Disk selection validation
  - File permission checks
  - Supported file type validation

### 4. Privilege Separation ✅
**Status: Implemented**

Disk operations now run in a separate privileged service with UAC elevation.

- **Module**: `privileged_operations.py` - `PrivilegedOperationHandler` class
- **Features**:
  - Unprivileged UI process
  - Separate privileged service (`exboot_privileged_service.exe`)
  - IPC via temporary request/response files
  - Operation validation before elevation
  - User context tracking

### 5. Operation Confirmation Dialogs ✅
**Status: Implemented**

Explicit confirmation required for all destructive operations.

- **Module**: `privileged_operations.py` - `OperationConfirmationDialog` class
- **Features**:
  - Dual-confirmation system
  - Case-sensitive confirmation text
  - Registry modification warnings
  - Audit logging of user decisions

### 6. Operation Rollback Framework ✅
**Status: Implemented**

Pre-operation snapshots and rollback capability.

- **Module**: `privileged_operations.py` - `OperationRollback` class
- **Features**:
  - Disk state snapshots before modifications
  - Rollback initiation framework
  - Snapshot retention policies

### 7. Comprehensive Audit Logging ✅
**Status: Implemented**

All security-critical operations are logged with full context.

- **Module**: `security_config.py` - `AuditLogger` class
- **Features**:
  - Disk operation logging
  - Registry modification logging
  - Update check logging
  - User and hostname tracking
  - Automatic log retention (90 days)
- **Log Location**: `%APPDATA%\Enosx Technologies\Exboot\audit_logs\`

### 8. Secure Update Mechanism ✅
**Status: Implemented**

Enhanced update checking with multiple verification layers.

- **Module**: `secure_update.py` - `SecureUpdateChecker` class
- **Features**:
  - GPG signature verification
  - SHA-256 hash verification
  - Code signing validation
  - Repository pinning
  - HTTPS-only downloads
  - TLS 1.2+ enforcement
  - Pre-release rejection

### 9. Ventoy Security ✅
**Status: Implemented**

Secure Ventoy downloading and verification.

- **Module**: `secure_update.py` - `VentoySecureDownloader` class
- **Features**:
  - HTTPS-only downloads from official repository
  - SHA-256 hash verification
  - Decompression bomb protection
  - Size limit enforcement (1GB max)
  - Timeout protections (120s)

### 10. Flash Disk Detection Fix ✅
**Status: Implemented**

Fixed USB drive detection to properly identify all removable media.

- **Changes**:
  - Improved PowerShell query for USB device detection
  - Better handling of drive letter assignment delays
  - Retry logic for newly connected drives

## Configuration

Security settings are centralized in `security_config.py`:

```python
SECURITY_CONFIG = {
    "max_iso_size_gb": 10,                    # Maximum ISO file size
    "max_zip_decompressed_gb": 20,           # Maximum decompressed ZIP size
    "update_check_interval_hours": 12,       # Update check frequency (was 6)
    "require_explicit_confirmation": True,    # Mandatory user confirmation
    "audit_log_retention_days": 90,          # Audit log retention period
    "require_code_signing": True,            # Require signed executables
    "minimum_tls_version": "1.2",            # Minimum TLS version
}
```

## Audit Logs

All security-critical operations are logged in JSON format:

```json
[2026-09-03 12:00:00] INFO: {"timestamp": "2026-09-03T12:00:00.000Z", "operation": "disk_format", "disk": "1", "user": "admin", "hostname": "COMPUTER", "details": {"status": "confirmed"}}
```

### Log Retention

- Audit logs are automatically cleaned up after 90 days
- Logs are stored in: `%APPDATA%\Enosx Technologies\Exboot\audit_logs\`
- Timestamp format: ISO 8601 UTC

## Update Verification

When Exboot checks for updates:

1. **HTTPS Connection**: Connects to GitHub API via HTTPS (TLS 1.2+)
2. **Release Verification**: Confirms release is from `enigmacxenosx/Exboot`
3. **Pre-release Check**: Rejects pre-release versions
4. **GPG Signature**: Verifies release was signed with trusted key
5. **File Download**: Downloads installer from GitHub releases
6. **Size Verification**: Checks downloaded file size matches expected
7. **Hash Verification**: Validates SHA-256 hash of installer
8. **Code Signing**: Verifies Authenticode signature on `.exe`
9. **Execution**: Runs verified installer with user confirmation

## USB Flash Drive Detection

Enhanced detection includes:

- All USB bus types (USB, USBSTOR)
- Removable media devices
- Multiple retry attempts for newly connected drives
- Improved drive letter assignment handling

## Recommendations for Users

### Before Using Exboot

1. **Verify Authenticity**
   - Download from official GitHub repository only
   - Check GPG signature if available
   - Verify file hash against release notes

2. **Backup Your Data**
   - Back up any data on USB drives before operation
   - Keep external backup of important files

3. **Review Disk Selection**
   - Carefully verify the correct USB drive is selected
   - Confirm disk size and name before proceeding
   - Do not proceed if unsure

### During Operation

1. **Read Confirmations Carefully**
   - Pay attention to warning dialogs
   - Type the exact confirmation text when required
   - Do not bypass confirmation steps

2. **Monitor Progress**
   - Keep Exboot window visible
   - Do not interrupt the operation
   - Do not unplug USB drive until complete

3. **Verify Completion**
   - Check log messages for success indicators
   - Verify USB drive is bootable if needed

### After Operation

1. **Review Audit Logs**
   - Check `%APPDATA%\Enosx Technologies\Exboot\audit_logs\` for operation records
   - Verify operations completed as expected

2. **Test Bootable Media**
   - Test USB drive on target hardware if applicable
   - Verify boot behavior meets expectations

3. **Report Issues**
   - Report any anomalies or errors via GitHub Issues
   - Include relevant audit log entries
   - Provide system information (Windows version, hardware)

## Known Limitations

1. **Full Rollback Not Supported**
   - Disk operations cannot be fully reversed automatically
   - Users should maintain backups before operations
   - Snapshot capability available for recovery planning

2. **GPG Verification**
   - Requires GPG to be installed on system
   - Keyserver access may be required
   - Air-gapped systems may need manual verification

3. **Code Signing**
   - Windows only (UAC requirement)
   - Requires .NET Framework for full Authenticode verification

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do Not** create a public GitHub issue
2. **Email** security details to: [security contact to be added]
3. **Include** reproduction steps, affected version, and impact assessment
4. **Wait** for acknowledgment before disclosing publicly

## Changelog

### v0.3.8+ (Security Hardening)

- ✅ Added `security_config.py` with GPG verification
- ✅ Added `privileged_operations.py` for privilege separation
- ✅ Added `secure_update.py` for secure update checking
- ✅ Fixed USB flash disk detection
- ✅ Implemented comprehensive audit logging
- ✅ Added operation confirmation dialogs
- ✅ Added operation rollback framework
- ✅ Implemented input validation for all user inputs
- ✅ Updated update check interval from 6 to 12 hours
- ✅ Added code signing verification
- ✅ Added Ventoy download verification

## Security References

- [Microsoft Authenticode Documentation](https://docs.microsoft.com/en-us/windows/win32/seccrypto/authenticode)
- [GPG Manual](https://www.gnupg.org/gph/en/manual.html)
- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [CWE-1021: Improper Restriction of Rendered UI Layers](https://cwe.mitre.org/data/definitions/1021.html)

## License

Security enhancements maintain the same license as Exboot main codebase.

---

**Last Updated**: September 3, 2026
**Document Version**: 1.0
