import argparse
import importlib.util
import os
import sys
import traceback
import concurrent.futures

from colorama import init, Fore, Style

init(autoreset=True)

BANNER = rf"""{Fore.CYAN}
      ___           ___           ___           ___           ___           ___           ___           ___           ___     
     /\__\         /\  \         /\__\         /\  \         /\  \         /\  \         /\  \         /\  \         /\__\    
    /:/  /        /::\  \       /::|  |       /::\  \       /::\  \       /::\  \       /::\  \       /::\  \       /::|  |   
   /:/__/        /:/\:\  \     /:|:|  |      /:/\:\  \     /:/\:\  \     /:/\:\  \     /:/\:\  \     /:/\:\  \     /:|:|  |   
  /::\  \ ___   /:/  \:\  \   /:/|:|  |__   /:/  \:\  \   /::\~\:\  \   /::\~\:\  \   /:/  \:\  \   /:/  \:\  \   /:/|:|  |__ 
 /:/\:\  /\__\ /:/__/ \:\__\ /:/ |:| /\__\ /:/__/_\:\__\ /:/\:\ \:\__\ /:/\:\ \:\__\ /:/__/ \:\__\ /:/__/ \:\__\ /:/ |:| /\__\
 \/__\:\/:/  / \:\  \ /:/  / \/__|:|/:/  / \:\  /\ \/__/ \/_|::\/:/  / \:\~\:\ \/__/ \:\  \  \/__/ \:\  \ /:/  / \/__|:|/:/  /
      \::/  /   \:\  /:/  /      |:/:/  /   \:\ \:\__\      |:|::/  /   \:\ \:\__\    \:\  \        \:\  /:/  /      |:/:/  / 
      /:/  /     \:\/:/  /       |::/  /     \:\/:/  /      |:|\/__/     \:\ \/__/     \:\  \        \:\/:/  /       |::/  /  
     /:/  /       \::/  /        /:/  /       \::/  /       |:|  |        \:\__\        \:\__\        \::/  /        /:/  /   
     \/__/         \/__/         \/__/         \/__/         \|__|         \/__/         \/__/         \/__/         \/__/    
{Style.RESET_ALL}"""


from core.config import load_config, ConfigError
from core.executor import run_command, RunStatus
from core.validation import (
    ValidationError,
    validate_target,
    validate_port,
    validate_output_dir,
    resolve_target,
)
from core.spinner import Spinner


# ---------------------------------------------------------------------------
# Nmap scan (unchanged logic, now via run_command)
# ---------------------------------------------------------------------------

def run_nmap_scan(target, output_dir, timeout):
    print(f"\n{Fore.YELLOW}[*] Starting Nmap scan on {target}...{Style.RESET_ALL}")
    xml_file = os.path.join(output_dir, "nmap_scan.xml")

    res = run_command(
        cmd=["nmap", "-sT", "-F", "-sV", "-oX", xml_file, target],
        message=f"Scanning {target}",
        timeout=timeout,
    )

    if res.status is RunStatus.NOT_FOUND:
        print(f"{Fore.RED}[-] Nmap is not installed.{Style.RESET_ALL}")
        return []
    if res.status is RunStatus.TIMEOUT:
        print(f"{Fore.RED}[-] Nmap timed out after {timeout}s.{Style.RESET_ALL}")
        return []
    if res.status is RunStatus.FAILED:
        print(f"{Fore.RED}[-] Nmap scan failed: {res.stderr[:200]}{Style.RESET_ALL}")
        return []

    print(f"{Fore.GREEN}[+] Nmap complete. Parsing XML...{Style.RESET_ALL}")

    from defusedxml import ElementTree as ET

    services = []
    try:
        root = ET.parse(xml_file).getroot()
        for port in root.findall(".//port"):
            state_el = port.find("state")
            if state_el is None or state_el.get("state") != "open":
                continue
            port_id = port.get("portid")
            svc_el = port.find("service")
            name = svc_el.get("name") if svc_el is not None else "unknown"
            services.append({"port": port_id, "service": name})
            print(f"    {Fore.MAGENTA}-> Open: {port_id} ({name}){Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[-] Error parsing XML: {e}{Style.RESET_ALL}")

    return services


# ---------------------------------------------------------------------------
# Plugin discovery + isolated execution
# ---------------------------------------------------------------------------

def discover_plugins(plugins_dir="plugins"):
    loaded = []
    if not os.path.isdir(plugins_dir):
        print(f"{Fore.RED}[-] Plugin directory '{plugins_dir}' missing.{Style.RESET_ALL}")
        return loaded

    for filename in os.listdir(plugins_dir):
        if not filename.endswith(".py") or filename == "__init__.py":
            continue

        mod_name = filename[:-3]
        path = os.path.join(plugins_dir, filename)
        spec = importlib.util.spec_from_file_location(mod_name, path)
        module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            print(f"{Fore.RED}[-] Failed to load {filename}: {e}{Style.RESET_ALL}")
            continue

        for obj in vars(module).values():
            if (
                isinstance(obj, type)
                and obj.__module__ == module.__name__
                and hasattr(obj, "name")
                and hasattr(obj, "run")
                and hasattr(obj, "should_run")
            ):
                try:
                    loaded.append(obj())
                except Exception as e:
                    print(f"{Fore.RED}[-] Plugin {obj.__name__} init failed: {e}{Style.RESET_ALL}")

    return loaded


def run_plugin_isolated(plugin, target, output_dir, port, service_name,
                        all_services, timeout):
    """Run a plugin in a thread with a timeout; never blocks the scan."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(plugin.run, target, output_dir, port, service_name, all_services)
        try:
            fut.result(timeout=timeout)
            return True, None
        except concurrent.futures.TimeoutError:
            return False, f"timed out after {timeout}s"
        except Exception as e:
            return False, repr(e)


def run_all_plugins(target, output_dir, all_services, timeout):
    print(f"\n{Fore.YELLOW}[*] Loading plugins...{Style.RESET_ALL}")
    plugins = discover_plugins()
    if not plugins:
        print(f"{Fore.RED}[-] No plugins found.{Style.RESET_ALL}")
        return

    print(f"{Fore.GREEN}[+] Loaded {len(plugins)} plugin(s).{Style.RESET_ALL}")

    for svc in all_services:
        port = svc["port"]
        name = svc["service"]
        for plugin in plugins:
            if not plugin.should_run(port, name, all_services):
                continue
            print(f"{Fore.GREEN}[+] {plugin.name} on {port} ({name}){Style.RESET_ALL}")
            ok, err = run_plugin_isolated(
                plugin, target, output_dir, port, name, all_services, timeout,
            )
            if not ok:
                print(f"{Fore.RED}[-] {plugin.name} failed: {err}{Style.RESET_ALL}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="HongRecon - Automated Reconnaissance Tool",
    )
    p.add_argument("-t", "--target", required=True,
                   help="Target IP, IPv6, or hostname")
    p.add_argument("-o", "--output", default="results",
                   help="Output directory (default: results)")
    p.add_argument("-p", "--port",
                   help="Skip Nmap and scan this port only")
    p.add_argument("-c", "--config", default="config.toml",
                   help="Config file (default: config.toml)")
    p.add_argument("--no-resolve", action="store_true",
                   help="Skip DNS resolution check on target")
    p.add_argument("--timeout", type=int, default=None,
                   help="Per-command timeout in seconds (overrides config)")
    return p.parse_args()


def main():
    print(BANNER)
    args = parse_args()

    # 1. Load config
    try:
        config = load_config(args.config)
    except ConfigError as e:
        print(f"{Fore.RED}[-] Config error: {e}{Style.RESET_ALL}")
        sys.exit(1)

    timeout = args.timeout or config["settings"]["timeout"]

    # 2. Validate target
    try:
        target = validate_target(args.target)
    except ValidationError as e:
        print(f"{Fore.RED}[-] {e}{Style.RESET_ALL}")
        sys.exit(1)

    # 3. Optional resolution
    if not args.no_resolve:
        try:
            resolved = resolve_target(target)
            print(f"{Fore.BLUE}[*] Target: {target} -> {resolved}{Style.RESET_ALL}")
        except ValidationError as e:
            print(f"{Fore.RED}[-] {e}{Style.RESET_ALL}")
            sys.exit(1)
    else:
        print(f"{Fore.BLUE}[*] Target: {target}{Style.RESET_ALL}")

    # 4. Validate output dir
    try:
        output_root = validate_output_dir(args.output)
    except ValidationError as e:
        print(f"{Fore.RED}[-] {e}{Style.RESET_ALL}")
        sys.exit(1)

    # 5. Validate --port if given
    if args.port:
        try:
            port = validate_port(args.port)
        except ValidationError as e:
            print(f"{Fore.RED}[-] {e}{Style.RESET_ALL}")
            sys.exit(1)
    else:
        port = None

    # 6. Prepare output dir
    target_dir = os.path.join(output_root, target)
    os.makedirs(target_dir, exist_ok=True)
    print(f"{Fore.BLUE}[*] Output: {target_dir}{Style.RESET_ALL}")

    # 7. Scan
    if port:
        print(f"\n{Fore.YELLOW}[*] Skipping Nmap, using port {port}{Style.RESET_ALL}")
        all_services = [{"port": port, "service": "unknown"}]
    else:
        all_services = run_nmap_scan(target, target_dir, timeout)

    if not all_services:
        print(f"\n{Fore.RED}[-] No open services found. Exiting.{Style.RESET_ALL}")
        return

    # 8. Run plugins
    run_all_plugins(target, target_dir, all_services, timeout)

    print(f"\n{Fore.CYAN}[✓] Done. Results in '{target_dir}'{Style.RESET_ALL}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Interrupted.{Style.RESET_ALL}")
        sys.exit(130)
    except Exception:
        print(f"\n{Fore.RED}[-] Unhandled error:{Style.RESET_ALL}")
        traceback.print_exc()
        sys.exit(1)