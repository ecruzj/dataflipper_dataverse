import os, subprocess, ctypes
from ctypes import wintypes

def _get_upn_via_winapi() -> str | None:
    # NameUserPrincipal = 8 (Windows Secur32)
    NameUserPrincipal = 8
    try:
        GetUserNameExW = ctypes.windll.secur32.GetUserNameExW  # type: ignore[attr-defined]
    except Exception:
        return None
    size = wintypes.ULONG(0)
    # First call to get required buffer size
    GetUserNameExW(NameUserPrincipal, None, ctypes.byref(size))
    if not size.value:
        return None
    buf = ctypes.create_unicode_buffer(size.value + 1)
    ok = GetUserNameExW(NameUserPrincipal, buf, ctypes.byref(size))
    return buf.value if ok and "@" in buf.value else None

def _get_upn_via_whoami() -> str | None:
    try:
        out = subprocess.check_output(["whoami", "/upn"], text=True, stderr=subprocess.STDOUT).strip()
        return out if out and "@" in out else None
    except Exception:
        return None

def get_current_user_email(default_domain: str = "ontario.ca") -> str | None:
    # 1) WinAPI (UPN)
    upn = _get_upn_via_winapi()
    if upn:
        return upn

    # 2) whoami /upn
    upn = _get_upn_via_whoami()
    if upn:
        return upn

    # 3) ENV fallback: DOMAIN\USERNAME => username@domain
    username = os.environ.get("USERNAME")
    dns_domain = os.environ.get("USERDNSDOMAIN")  # e.g. ONTARIO.CA
    domain = (dns_domain or default_domain or "").lower()
    if username and domain:
        return f"{username}@{domain}"
    return None
