import argparse
import os
import toml
import importlib.util
import subprocess
from colorama import init, Fore, Style # Fixed typo: colorama
from defusedxml import ElementTree as ET

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

def load_config():
    """Reads the config.toml file"""
    try:
        return toml.load("config.toml")
    except FileNotFoundError:
        print(f"{Fore.RED}[-] Error: config.toml not found!{Style.RESET_ALL}")
        return {}

def load_plugins(target, output_dir): # Fixed naming to match call
    """ 
    Scans the 'plugins' folder and loads all python files.
    """
    plugins_dir = "plugins"
    print(f"\n{Fore.YELLOW}[*] Loading plugins...{Style.RESET_ALL}")

    for filename in os.listdir(plugins_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            plugin_name = filename[:-3]

            if plugin_name == "http" and "80" not in open_ports:
                continue

            if plugin_name == "ftp" and "21" not in open_ports:
                continue

            file_path = os.path.join(plugins_dir, filename)
            spec = importlib.util.spec_from_file_location(plugin_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "run"):
                print(f"{Fore.GREEN} [+] Executing Plugin: {plugin_name}{Style.RESET_ALL}")
                module.run(target, output_dir, open_ports)
            else:
                print(f"{Fore.RED} [-] Plugin {plugin_name} missing 'run()' function.{Style.RESET_ALL}") # Fixed missing quote

def main():
    print(BANNER)

    parser = argparse.ArgumentParser (description ="HongRecon - Automated Reconnaissance Tool")
    
    parser.add_argument("-t", "--target", required=True, help="Target IP or Hostname")

    parser.add_argument("-o", "--output", default="results", help="Output directory (default: results)")

    args = parser.parse_args()

    config = load_config()

    target_dir = os.path.join(args.output, args.target)
    os.makedirs(target_dir, exist_ok=True)
    print(f"{Fore.BLUE}[*] Target set to: {args.target}")
    print(f"[*] Output directory: {target_dir}")

    load_plugins(args.target, target_dir)

    print(f"\n{Fore.CYAN}[✓] Reconnaissance completed! Check Results in the '{target_dir}' folder for results.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()