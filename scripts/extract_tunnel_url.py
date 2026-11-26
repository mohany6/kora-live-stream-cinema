import re
import sys
import time
import subprocess
from pathlib import Path

TUNNEL_REGEX = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

def parse_trycloudflare_url(text: str) -> str | None:
    """Extract the first trycloudflare.com URL from log output."""
    match = TUNNEL_REGEX.search(text)
    return match.group(0) if match else None

def wait_for_tunnel_url(log_file_path: Path, timeout_seconds: int = 30) -> str | None:
    """Poll log file until trycloudflare URL appears or timeout expires."""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        if log_file_path.exists():
            try:
                content = log_file_path.read_text(encoding="utf-8", errors="ignore")
                url = parse_trycloudflare_url(content)
                if url:
                    return url
            except Exception:
                pass
        time.sleep(1)
    return None

def copy_to_clipboard(text: str) -> bool:
    """Copy text to Windows clipboard using clip.exe without admin rights."""
    try:
        process = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
        process.communicate(input=text.encode("utf-8"))
        return process.returncode == 0
    except Exception:
        return False

def main():
    log_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".tools/tunnel.log")
    out_path = Path("data/tunnel_url.txt")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Waiting for Cloudflare Tunnel URL in {log_path}...")
    url = wait_for_tunnel_url(log_path, timeout_seconds=30)
    if url:
        out_path.write_text(url, encoding="utf-8")
        copied = copy_to_clipboard(url)
        print("\n" + "=" * 60)
        print(" [OK] Kora Live Platform is now PUBLIC & LIVE on the internet!")
        print(f" [URL] {url}")
        if copied:
            print(" [CLIPBOARD] URL has been automatically copied to your clipboard!")
        print("=" * 60 + "\n")
    else:
        print("\n[-] Timeout waiting for Cloudflare Tunnel URL. Check .tools/tunnel.log for details.\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
