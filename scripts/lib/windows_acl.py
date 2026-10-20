"""Owner-only file protection on Windows, the equivalent of POSIX mode 0600.

The check reads the file's security descriptor as SDDL through the Windows
API rather than parsing icacls output, whose account names are localised.
"""
from __future__ import annotations

import ctypes
import re
import subprocess
import sys
from pathlib import Path

SE_FILE_OBJECT = 1
OWNER_SECURITY_INFORMATION = 0x1
DACL_SECURITY_INFORMATION = 0x4
SDDL_REVISION_1 = 1
# Besides the owner, only SYSTEM, Administrators and OWNER RIGHTS may hold access.
WELL_KNOWN = {"SY": "S-1-5-18", "BA": "S-1-5-32-544", "OW": "S-1-3-4"}
TRUSTED = set(WELL_KNOWN.values())
ALLOW_TYPES = {"A", "OA", "XA", "ZA"}
NAMES = {"WD": "Everyone", "BU": "Users", "AU": "Authenticated Users", "IU": "interactive users"}
ACE = re.compile(r"\(([^;()]*);([^;()]*);[^;()]*;[^;()]*;[^;()]*;([^;()]*)[^()]*\)")


def _sid(value: str) -> str:
    return WELL_KNOWN.get(value, value)


def sddl(path: Path) -> str:
    """Owner and DACL of PATH as an SDDL string."""
    from ctypes import wintypes

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi32.GetNamedSecurityInfoW.argtypes = [
        wintypes.LPCWSTR, ctypes.c_int, wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    advapi32.GetNamedSecurityInfoW.restype = wintypes.DWORD
    advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(wintypes.LPWSTR), ctypes.c_void_p]
    advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]

    info = OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION
    descriptor = ctypes.c_void_p()
    status = advapi32.GetNamedSecurityInfoW(str(path), SE_FILE_OBJECT, info, None, None, None, None,
                                            ctypes.byref(descriptor))
    if status:
        raise OSError(status, ctypes.FormatError(status), str(path))
    try:
        text = wintypes.LPWSTR()
        if not advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW(
                descriptor, SDDL_REVISION_1, info, ctypes.byref(text), None):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return text.value or ""
        finally:
            kernel32.LocalFree(ctypes.cast(text, ctypes.c_void_p))
    finally:
        kernel32.LocalFree(descriptor)


def owner_only_problem(path: Path) -> str | None:
    """Why PATH is readable by someone other than its owner, or None if it is not."""
    text = sddl(path)
    owner = re.match(r"O:([A-Z]{2}|S-[0-9-]+)", text)
    if owner is None or "D:" not in text:
        return "its access control list could not be read"
    dacl = text.split("D:", 1)[1]
    if dacl.startswith("NO_ACCESS_CONTROL"):
        return "it has no access control list, so everyone can read it"
    allowed = TRUSTED | {_sid(owner.group(1))}
    for ace_type, flags, account in ACE.findall(dacl):
        if "IO" in re.findall("..", flags):
            continue  # inherit-only entries do not apply to the file itself
        if ace_type in ALLOW_TYPES and _sid(account) not in allowed:
            return f"it grants access to {NAMES.get(account, _sid(account))}"
    return None


def restrict_to_owner(path: Path) -> None:
    """Replace PATH's access list with full control for its owner only."""
    owner = re.match(r"O:([A-Z]{2}|S-[0-9-]+)", sddl(path))
    if owner is None:
        raise OSError(f"cannot read the owner of {path}")
    subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", f"*{_sid(owner.group(1))}:F"],
                   check=True, capture_output=True)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("check", "restrict"):
        raise SystemExit("usage: windows_acl.py check|restrict PATH")
    target = Path(sys.argv[2])
    if sys.argv[1] == "restrict":
        restrict_to_owner(target)
    problem = owner_only_problem(target)
    if problem:
        raise SystemExit(f"{target}: {problem}")
