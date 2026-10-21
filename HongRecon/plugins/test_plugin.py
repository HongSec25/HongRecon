# plugins/test_plugin.py
from colorama import Fore, Style

def run(target, output_dir):
    """
    Every plugin MUST have this exact 'run' function. 
    PyRecon will pass the target IP and the output directory to it.
    """
    print(f"    {Fore.MAGENTA}-> Test plugin is successfully running against {target}!{Style.RESET_ALL}")
    
    # Let's write a dummy file to prove it works
    with open(f"{output_dir}/test_output.txt", "w") as f:
        f.write(f"Plugin tested against {target}. It works!")