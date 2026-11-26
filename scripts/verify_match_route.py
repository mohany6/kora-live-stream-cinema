import urllib.request
from pathlib import Path

def check_route():
    tunnel_file = Path("data/tunnel_url.txt")
    tunnel_url = tunnel_file.read_text(encoding="utf-8-sig").strip() if tunnel_file.exists() else ""
    
    # Check local
    req = urllib.request.Request("http://127.0.0.1:8000/match/401915378", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=5) as res:
        print(f"Local status: {res.status}, Length: {len(res.read())}")

    # Check Cloudflare tunnel
    if tunnel_url:
        target = f"{tunnel_url}/match/401915378"
        print(f"Testing tunnel URL: {target}")
        req_tunnel = urllib.request.Request(target, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_tunnel, timeout=10) as res_tunnel:
            print(f"Tunnel status: {res_tunnel.status}, Length: {len(res_tunnel.read())}")

if __name__ == "__main__":
    check_route()

