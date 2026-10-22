import subprocess
from dataclasses import dataclass
from enum import Enum

from .spinner import Spinner


class RunStatus(Enum):
    OK = "ok"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"
    FAILED = "failed"


@dataclass
class RunResult:
    status: RunStatus
    stderr: str = ""
    returncode: int = 0

    @property
    def ok(self) -> bool:
        return self.status is RunStatus.OK


def run_command(cmd, message, timeout=300, hide_output=True) -> RunResult:
    """
    Run a shell command with a spinner and a hard timeout.

    Returns a RunResult. Never raises — callers branch on `result.status`.
    """
    stdout = subprocess.PIPE if hide_output else None
    stderr = subprocess.PIPE if hide_output else None

    with Spinner(message):
        try:
            proc = subprocess.run(
                cmd,
                check=True,
                timeout=timeout,
                stdout=stdout,
                stderr=stderr,
                text=True,
            )
            return RunResult(RunStatus.OK, "", proc.returncode or 0)
        except subprocess.TimeoutExpired:
            return RunResult(RunStatus.TIMEOUT, f"Timed out after {timeout}s")
        except subprocess.CalledProcessError as e:
            return RunResult(
                RunStatus.FAILED,
                (e.stderr or "").strip(),
                e.returncode,
            )
        except FileNotFoundError:
            return RunResult(RunStatus.NOT_FOUND, "Binary not installed")
        except Exception as e:
            return RunResult(RunStatus.FAILED, repr(e))