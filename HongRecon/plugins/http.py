from colorama import Fore, Style

def run(target, output_dir, open_ports):
    # Because our main script filtered it, we know Port 80 is open!
    print(f"    {Fore.CYAN}[HTTP] Target {target} has a web server. Preparing FFUF next week!{Style.RESET_ALL}")
    
    # We can save a file
    with open(f"{output_dir}/web_info.txt", "w") as f:
        f.write(f"Web server found at http://{target}")