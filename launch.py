"""一键启动两个本地服务，并展示局域网扫码二维码。"""
import os
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import qrcode

ROOT = Path(__file__).resolve().parent


def lan_ip():
    """查询当前默认网卡IP，不会传输任何数据。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def main():
    ip = os.getenv("DEMO_LAN_IP", lan_ip())
    url = f"http://{ip}:8501"
    print("\n手机打开：", url, "\n")
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    env = dict(os.environ, DEMO_URL=url)
    backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=ROOT, env=env)
    frontend = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "frontend.py", "--server.address", "127.0.0.1" if "--public" in sys.argv else "0.0.0.0", "--server.port", "8501", "--server.headless", "true"], cwd=ROOT, env=env)
    tunnel = None
    url_file = ROOT / "data" / "public_url.txt"
    if "--public" in sys.argv:
        url_file.unlink(missing_ok=True)
        try:
            tunnel = subprocess.Popen(["cloudflared", "tunnel", "--url", "http://127.0.0.1:8501"], cwd=ROOT, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, bufsize=1)
        except FileNotFoundError:
            print("未找到 cloudflared。请先安装，详见 README；公网模式未启动。")
        if tunnel:
            def show_public_url():
                # cloudflared 在 stderr 输出临时域名；不会创建需要账户的永久服务。
                for line in tunnel.stderr:
                    found = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
                    if found:
                        public_url = found.group(0)
                        url_file.write_text(public_url, encoding="utf-8")
                        print("\n公网扫码链接：", public_url, flush=True)
                        public_qr = qrcode.QRCode(border=1)
                        public_qr.add_data(public_url)
                        public_qr.make(fit=True)
                        public_qr.print_ascii(invert=True)
                        break
            threading.Thread(target=show_public_url, daemon=True).start()
    try:
        frontend.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for process in (frontend, backend, tunnel):
            if process is None:
                continue
            process.terminate()
        for process in (frontend, backend, tunnel):
            if process is None:
                continue
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        if "--public" in sys.argv:
            url_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
