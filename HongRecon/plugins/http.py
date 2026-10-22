import json
import os

from colorama import Fore, Style

from core.executor import run_command, RunStatus


class HttpDirectoryFuzzing:
    name = "HTTP Directory Fuzzing"

    def should_run(self, port, service_name, all_services):
        standard = {"80", "443", "8080", "8000"}
        if port in standard or service_name in ("http", "https", "http-proxy", "www"):
            return True

        try:
            port_num = int(port)
        except (TypeError, ValueError):
            return False

        if any(s["port"] in standard for s in all_services):
            return False
        if port_num <= 1024:
            return False

        highs = sorted(
            int(s["port"]) for s in all_services
            if str(s["port"]).isdigit() and int(s["port"]) > 1024
        )
        return bool(highs) and port_num == highs[0]

    def run(self, target, output_dir, port, service_name, all_services):
        print(f"    {Fore.CYAN}[HTTP] Fuzzing {target}:{port}...{Style.RESET_ALL}")

        web_dir = os.path.join(output_dir, "web")
        os.makedirs(web_dir, exist_ok=True)

        # Try seclists first, fall back to bundled wordlist
        wordlist_candidates = [
            "/usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt",
            "/usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt",
            "wordlists/common-dirs.txt",
        ]
        wordlist = next((w for w in wordlist_candidates if os.path.exists(w)), None)
        if not wordlist:
            print(f"    {Fore.RED}[-] No wordlist found. Skipping ffuf.{Style.RESET_ALL}")
            return

        scheme = "https" if port == "443" or "ssl" in service_name or "https" in service_name else "http"
        host_part = target if port in ("80", "443") else f"{target}:{port}"
        url = f"{scheme}://{host_part}/FUZZ"

        out_json = os.path.join(web_dir, f"ffuf_{port}.json")

        res = run_command(
            cmd=[
                "ffuf", "-w", wordlist, "-u", url,
                "-o", out_json, "-of", "json",
                "-mc", "200,204,301,302,403",
            ],
            message=f"Fuzzing {url}",
            timeout=300,
        )

        if res.status is RunStatus.NOT_FOUND:
            print(f"    {Fore.RED}[-] ffuf not installed.{Style.RESET_ALL}")
            return
        if res.status is RunStatus.TIMEOUT:
            print(f"    {Fore.YELLOW}[*] ffuf timed out after 300s.{Style.RESET_ALL}")
            return
        if res.status is RunStatus.FAILED:
            err = res.stderr[:200] if res.stderr else "unknown error"
            print(f"    {Fore.RED}[-] ffuf failed: {err}{Style.RESET_ALL}")
            return

        # Parse and display results inline (no import from hongrecon.py)
        self._display_results(out_json)

    def _display_results(self, json_file):
        try:
            with open(json_file) as f:
                data = json.load(f)
        except Exception as e:
            print(f"    {Fore.RED}[-] Could not read ffuf output: {e}{Style.RESET_ALL}")
            return

        results = data.get("results", [])
        if not results:
            print(f"    {Fore.YELLOW}[*] No directories found.{Style.RESET_ALL}")
            return

        for r in results:
            status = r.get("status", "?")
            url = r.get("url", r.get("input", {}).get("FUZZ", "?"))
            if status == 200:
                color = Fore.GREEN
            elif status in (301, 302):
                color = Fore.YELLOW
            elif status == 403:
                color = Fore.MAGENTA
            else:
                color = Fore.WHITE
            print(f"        {color}-> [{status}] {url}{Style.RESET_ALL}")