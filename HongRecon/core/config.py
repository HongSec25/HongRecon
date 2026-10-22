import os

import toml
from colorama import Fore, Style


DEFAULTS = {
    "settings": {
        "threads": 10,
        "timeout": 300,
    },
    "wordlists": {
        "dirb": "/usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt",
    },
}


class ConfigError(Exception):
    """Raised when config.toml is malformed or invalid."""


def _merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _validate(cfg: dict) -> None:
    s = cfg["settings"]

    if not isinstance(s["timeout"], int) or s["timeout"] <= 0:
        raise ConfigError(f"settings.timeout must be positive int (got {s['timeout']!r})")
    if not isinstance(s["threads"], int) or s["threads"] < 1:
        raise ConfigError(f"settings.threads must be positive int (got {s['threads']!r})")


def load_config(path: str = "config.toml") -> dict:
    if not os.path.exists(path):
        print(f"{Fore.YELLOW}[*] {path} not found, using defaults.{Style.RESET_ALL}")
        cfg = _merge(DEFAULTS, {})
        _validate(cfg)
        return cfg

    try:
        raw = toml.load(path)
    except toml.TomlDecodeError as e:
        raise ConfigError(f"Failed to parse {path}: {e}") from e
    except OSError as e:
        raise ConfigError(f"Cannot read {path}: {e}") from e

    cfg = _merge(DEFAULTS, raw)
    _validate(cfg)
    return cfg