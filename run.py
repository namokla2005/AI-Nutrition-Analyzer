"""Điểm khởi chạy website AI Nutrition Analyzer.

Cách dùng:
    .venv\\Scripts\\python.exe run.py                 # chạy bình thường
    .venv\\Scripts\\python.exe run.py --reload        # chế độ phát triển
    .venv\\Scripts\\python.exe run.py --port 9000
    .venv\\Scripts\\python.exe run.py --no-browser

Hoặc nhấp đúp vào START_WEBSITE.bat ở thư mục gốc.
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def _port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def _find_port(host: str, start: int) -> int:
    for port in range(start, start + 20):
        if _port_free(host, port):
            return port
    raise SystemExit(f"Không tìm được cổng trống từ {start} đến {start + 19}.")


def _open_browser_later(url: str, delay: float = 2.0) -> None:
    def _job() -> None:
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:  # pragma: no cover - phụ thuộc môi trường desktop
            pass

    threading.Thread(target=_job, daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy website AI Nutrition Analyzer")
    parser.add_argument("--host", default=None, help="Địa chỉ lắng nghe (mặc định từ .env)")
    parser.add_argument("--port", type=int, default=None, help="Cổng (mặc định từ .env)")
    parser.add_argument("--reload", action="store_true", help="Tự nạp lại khi sửa code")
    parser.add_argument("--no-browser", action="store_true", help="Không tự mở trình duyệt")
    parser.add_argument("--auto-port", action="store_true", help="Tự chọn cổng trống nếu cổng bận")
    args = parser.parse_args()

    from app.core.config import BASE_DIR as PROJ, settings
    from app.core.database import db_path_from_url

    settings.ensure_dirs()

    host = args.host or settings.host
    port = args.port or settings.port

    if not _port_free(host, port):
        if args.auto_port:
            new_port = _find_port(host, port + 1)
            print(f"[!] Cổng {port} đang được dùng -> chuyển sang {new_port}")
            port = new_port
        else:
            print(f"[!] CẢNH BÁO: cổng {port} đang được dùng. Dùng --auto-port để tự chọn cổng khác.")

    db_file = db_path_from_url()
    if db_file and not db_file.exists():
        print("[!] Chưa có database. Hãy chạy: scripts\\init_db.bat (hoặc alembic upgrade head)")

    url = f"http://{'127.0.0.1' if host in ('0.0.0.0', '') else host}:{port}"
    print("=" * 62)
    print("  AI NUTRITION ANALYZER")
    print(f"  Website : {url}")
    print(f"  API doc : {url}/docs")
    print(f"  Database: {db_file}")
    print(f"  Ollama  : {settings.ollama_base_url} ({settings.ollama_model})")
    print("  Dừng   : nhấn Ctrl+C")
    print("=" * 62)

    if not args.no_browser:
        _open_browser_later(url)

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=args.reload,
        log_level="debug" if settings.debug else "info",
        app_dir=PROJ,
    )


if __name__ == "__main__":
    main()
