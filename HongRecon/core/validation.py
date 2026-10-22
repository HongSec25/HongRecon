import ipaddress
import re
import socket


class ValidationError(Exception):
    """Raised when user input is invalid."""


_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)"
    r"(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
)

_RESERVED_TARGET_CHARS = set("/\\:*?\"<>|")


def validate_target(target: str) -> str:
    """Validate an IP, IPv6, or hostname. Returns normalized form."""
    if not target or not target.strip():
        raise ValidationError("Target is empty.")

    target = target.strip()

    if any(c in _RESERVED_TARGET_CHARS for c in target):
        raise ValidationError(
            f"'{target}' contains characters not allowed in a target "
            f"(/, \\, :, *, ?, \", <, >, |)."
        )

    try:
        ip = ipaddress.ip_address(target)
        return str(ip)
    except ValueError:
        pass

    if _HOSTNAME_RE.match(target):
        return target.lower()

    raise ValidationError(
        f"'{target}' is not a valid IPv4/IPv6 address or hostname."
    )


def validate_port(port: str) -> str:
    """Validate a port or port range like '80' or '80-443'."""
    if not port or not port.strip():
        raise ValidationError("Port is empty.")
    port = port.strip()

    def _check(p: str) -> int:
        if not p.isdigit():
            raise ValidationError(f"'{p}' is not a valid port number.")
        n = int(p)
        if not 1 <= n <= 65535:
            raise ValidationError(f"Port {n} out of range (1-65535).")
        return n

    if "-" in port:
        lo, _, hi = port.partition("-")
        lo_n, hi_n = _check(lo), _check(hi)
        if lo_n >= hi_n:
            raise ValidationError(f"Port range '{port}' invalid (low >= high).")
        return f"{lo_n}-{hi_n}"

    return str(_check(port))


def validate_output_dir(path: str) -> str:
    if not path or not path.strip():
        raise ValidationError("Output directory is empty.")
    return path.strip()


def resolve_target(target: str) -> str:
    """Best-effort DNS resolution to confirm target exists."""
    try:
        return socket.gethostbyname(target)
    except socket.gaierror as e:
        raise ValidationError(
            f"Cannot resolve '{target}': {e}. "
            f"Check spelling/DNS or use --no-resolve."
        ) from e