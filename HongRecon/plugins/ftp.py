import ftplib

from colorama import Fore, Style


class FtpAnonymousLogin:
    name = "FTP Anonymous Login Check"

    def should_run(self, port, service_name, all_services):
        return port == "21" or service_name == "ftp"

    def run(self, target, output_dir, port, service_name, all_services):
        print(f"   {Fore.CYAN}[FTP] Checking anonymous login on {target}:{port}...{Style.RESET_ALL}")
        ftp = None
        try:
            ftp = ftplib.FTP(timeout=5)
            ftp.connect(target, int(port))
            ftp.login()

            # Login succeeded — this IS a vulnerability regardless of listing.
            try:
                files = ftp.nlst()
                print(f"   {Fore.RED}[!] VULNERABILITY: Anonymous FTP login allowed!{Style.RESET_ALL}")
                print(f"   {Fore.GREEN}[+] Files found: {files}{Style.RESET_ALL}")
                with open(f"{output_dir}/ftp_anon_{port}.txt", "w") as f:
                    f.write(f"Anonymous login successful on port {port}.\nFiles:\n")
                    for name in files:
                        f.write(f"- {name}\n")
            except ftplib.error_perm:
                print(f"   {Fore.RED}[!] VULNERABILITY: Anonymous login allowed "
                      f"(listing denied).{Style.RESET_ALL}")
                with open(f"{output_dir}/ftp_anon_{port}.txt", "w") as f:
                    f.write(f"Anonymous login successful on port {port}.\n"
                            f"Directory listing was denied by the server.\n")

        except ftplib.error_perm:
            # This means login() itself was rejected — server is secure.
            print(f"   {Fore.GREEN}[-] Anonymous login denied (server is secure).{Style.RESET_ALL}")
        except ftplib.all_errors as e:
            print(f"   {Fore.RED}[-] FTP connection failed: {e}{Style.RESET_ALL}")
        finally:
            if ftp:
                try:
                    ftp.quit()
                except Exception:
                    pass