import sys
import threading
import time

from colorama import Fore, Style


class Spinner:
    def __init__(self, message="Loading ...", interval=0.1):
        self.message = message
        self.interval = interval
        self._spinning = False
        self._chars = ["|", "/", "-", "\\"]
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        i = 0
        while self._spinning:
            sys.stdout.write(
                f"\r  {Fore.YELLOW}{self._chars[i % len(self._chars)]}"
                f"{Style.RESET_ALL} {self.message}"
            )
            sys.stdout.flush()
            i += 1
            time.sleep(self.interval)
        # Clear the spinner line before handing control back.
        sys.stdout.write(f"\r{' ' * (len(self.message) + 15)}\r")
        sys.stdout.flush()

    def start(self):
        if self._spinning:
            return self
        self._spinning = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._spinning = False
        if self._thread.is_alive():
            self._thread.join(timeout=max(1.0, self.interval * 5))

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()