"""Sao lưu database SQLite (§7.6 yêu cầu có cơ chế backup).

Dùng API `sqlite3.Connection.backup` - sao lưu an toàn ngay cả khi có kết nối đang mở
(khác với copy file trực tiếp khi đang bật WAL, dễ ra bản sao hỏng).

Chạy:
    .venv\\Scripts\\python.exe scripts\\backup_db.py
    .venv\\Scripts\\python.exe scripts\\backup_db.py --keep 14
    .venv\\Scripts\\python.exe scripts\\backup_db.py --verify data\\backups\\nutrition_20261119_031500.db
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app.core.database import db_path_from_url  # noqa: E402
from app.core.utils import human_bytes  # noqa: E402


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def integrity_check(path: Path) -> str:
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        return str(con.execute("PRAGMA integrity_check").fetchone()[0])
    finally:
        con.close()


def make_backup(db_file: Path, backup_dir: Path, label: str | None = None) -> Path:
    if not db_file.exists():
        raise SystemExit(f"[X] Không tìm thấy database: {db_file}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    name = f"nutrition_{stamp}{('_' + label) if label else ''}.db"
    dest = backup_dir / name

    src = sqlite3.connect(db_file.as_posix())
    try:
        dst = sqlite3.connect(dest.as_posix())
        try:
            src.backup(dst)  # bản sao nhất quán kể cả khi DB đang được ghi
            # Ghi chú: DB nguồn đang ở chế độ WAL nên bản sao cũng mang chế độ WAL,
            # tức là cần checkpoint rồi chuyển về chế độ DELETE để bản sao lưu là
            # MỘT file duy nhất, tự chứa (không còn phụ thuộc file -wal/-shm).
            dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            dst.execute("PRAGMA journal_mode=DELETE")
            dst.commit()
        finally:
            dst.close()
    finally:
        src.close()

    stale = [dest.with_name(dest.name + suffix) for suffix in ("-wal", "-shm")]
    for extra in stale:
        if extra.exists():
            extra.unlink()
    leftover = [p.name for p in stale if p.exists()]

    status = integrity_check(dest)
    size = dest.stat().st_size
    print(f"[v] Đã sao lưu: {dest}")
    print(f"    Kích thước      : {human_bytes(size)} ({size} B)")
    print(f"    integrity_check : {status}")
    print(f"    sha256          : {sha256_file(dest)}")
    print(f"    File -wal/-shm  : {'còn sót ' + str(leftover) if leftover else 'không (bản sao tự chứa)'}")
    if status != "ok":
        raise SystemExit("[X] Bản sao lưu không qua kiểm tra toàn vẹn!")
    if leftover:
        raise SystemExit("[X] Bản sao lưu vẫn còn file phụ -wal/-shm, không tự chứa!")
    return dest


def rotate(backup_dir: Path, keep: int) -> list[Path]:
    files = sorted(backup_dir.glob("nutrition_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    removed: list[Path] = []
    for old in files[keep:]:
        old.unlink()
        removed.append(old)
    return removed


def main() -> int:
    ap = argparse.ArgumentParser(description="Sao lưu database AI Nutrition Analyzer")
    ap.add_argument("--db", default=None, help="Đường dẫn database (mặc định: theo cấu hình .env)")
    ap.add_argument("--out", default=None, help="Thư mục chứa bản sao lưu")
    ap.add_argument("--keep", type=int, default=10, help="Số bản sao lưu giữ lại (mặc định 10)")
    ap.add_argument("--label", default=None, help="Nhãn thêm vào tên file, ví dụ: truoc_khi_import")
    ap.add_argument("--verify", default=None, help="Chỉ kiểm tra toàn vẹn một file backup có sẵn")
    args = ap.parse_args()

    if args.verify:
        p = Path(args.verify)
        print(f"File      : {p}")
        print(f"integrity : {integrity_check(p)}")
        print(f"sha256    : {sha256_file(p)}")
        return 0

    db_file = Path(args.db) if args.db else (db_path_from_url() or Path())
    backup_dir = Path(args.out) if args.out else (BASE_DIR / "data" / "backups")

    dest = make_backup(db_file, backup_dir, args.label)
    removed = rotate(backup_dir, max(1, args.keep))
    if removed:
        print(f"[i] Đã xóa {len(removed)} bản sao lưu cũ (giữ lại {args.keep}):")
        for p in removed:
            print(f"    - {p.name}")
    total = len(list(backup_dir.glob("nutrition_*.db")))
    print(f"[i] Tổng số bản sao lưu hiện có: {total}")
    print(f"[i] Backup mới nhất: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
