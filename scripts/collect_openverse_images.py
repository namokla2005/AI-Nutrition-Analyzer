#!/usr/bin/env python3
"""Collect and audit freely licensed food images from Openverse.

The collector is intentionally independent from the Commons collector. It writes
``ov_<first-8-id>.jpg`` files, same-stem JSON sidecars, Openverse-only provenance
reports, and paginated contact sheets for visual review.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

API = "https://api.openverse.org/v1/images/"
USER_AGENT = (
    "AI-Nutrition-Analyzer-Openverse-Collector/1.0 "
    "(academic dataset; contact: https://github.com/namokla2005/AI-Nutrition-Analyzer)"
)
REQUEST_INTERVAL = 1.05
ALLOWED_LICENSES = {"cc0", "by", "by-sa", "pdm", "public-domain", "public domain"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp"}
FIELDS = [
    "id", "title", "url", "thumbnail", "foreign_landing_url", "creator",
    "license", "license_version", "license_url", "provider", "source", "width",
    "height", "filesize",
]
PROVENANCE_FIELDS = [
    "our_class", "local_file", *FIELDS, "query", "downloaded_from", "sha256",
    "stored_width", "stored_height", "downloaded_bytes", "review_status",
]
DEFAULT_SPECS = {
    "canh_chua": ["canh chua", "Vietnamese sour soup", "Vietnamese sweet sour fish soup", "Vietnamese tamarind soup", "canh chua ca"],
    "banh_beo": ["banh beo", "bánh bèo", "Vietnamese steamed rice cake", "Vietnamese water fern cake", "water fern cakes"],
    "banh_khot": ["banh khot", "bánh khọt", "Vietnamese savory mini pancake", "Vietnamese mini savory pancake", "Vietnamese coconut shrimp pancake"],
    "bun_dau_mam_tom": ["bun dau mam tom", "bún đậu mắm tôm", "bun dau", "Vietnamese tofu vermicelli", "Vietnamese tofu platter", "tofu vermicelli platter", "mam tom tofu"],
    "bun_rieu": ["bun rieu", "bún riêu", "Vietnamese crab noodle soup"],
    "bun_thit_nuong": ["bun thit nuong", "bún thịt nướng", "grilled pork vermicelli"],
    "pho_ga": ["pho ga", "phở gà", "chicken pho"],
}
DEFAULT_TARGETS = {
    "canh_chua": 40,
    "banh_beo": 35,
    "banh_khot": 25,
    "bun_dau_mam_tom": 30,
    "bun_rieu": 35,
    "bun_thit_nuong": 35,
    "pho_ga": 35,
}
_last_request_at = 0.0


def paced_open(request: Request, timeout: int = 60):
    global _last_request_at
    delay = REQUEST_INTERVAL - (time.monotonic() - _last_request_at)
    if delay > 0:
        time.sleep(delay)
    try:
        return urlopen(request, timeout=timeout)
    finally:
        _last_request_at = time.monotonic()


def fetch(url: str, accept: str, retries: int = 5) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    for attempt in range(retries):
        try:
            with paced_open(request) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code != 429 and 400 <= exc.code < 500:
                raise
            if attempt + 1 == retries:
                raise
            retry_after = exc.headers.get("Retry-After")
            time.sleep(float(retry_after) if retry_after and retry_after.isdigit() else 2 ** (attempt + 1))
        except (URLError, TimeoutError, OSError):
            if attempt + 1 == retries:
                raise
            time.sleep(2 ** (attempt + 1))
    raise AssertionError("unreachable")


def api_page(query: str, page: int) -> dict[str, Any]:
    params = {
        "q": query,
        # Openverse currently caps anonymous requests at 20 results per page.
        "page_size": 20,
        "page": page,
        "license": "cc0,by,by-sa",
        "license_type": "commercial,modification",
    }
    return json.loads(fetch(f"{API}?{urlencode(params)}", "application/json").decode("utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def existing_hashes(class_dir: Path) -> set[str]:
    return {
        sha256(path) for path in class_dir.glob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    }


def valid_dimensions(width: Any, height: Any) -> bool:
    try:
        w, h = int(width), int(height)
    except (TypeError, ValueError):
        return False
    return max(w, h) >= 400 and min(w, h) >= 300


def normalized_id(value: Any) -> str:
    return str(value or "").strip().lower()


def collect_class(project: Path, class_name: str, queries: list[str], target: int) -> dict[str, Any]:
    class_dir = project / "data" / "raw" / "images" / class_name
    class_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = project / "data" / "processed" / ".openverse_downloads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    hashes = existing_hashes(class_dir)
    known_ids = set()
    rejected_dir = project / "data" / "raw" / "images" / "_rejected" / class_name
    for sidecar in [*class_dir.glob("ov_*.json"), *rejected_dir.glob("ov_*.json")]:
        try:
            known_ids.add(normalized_id(json.loads(sidecar.read_text(encoding="utf-8")).get("id")))
        except (OSError, json.JSONDecodeError):
            pass
    seen = set(known_ids)
    stats: dict[str, Any] = {
        "our_class": class_name, "target": target, "queries": queries, "api_candidates": 0,
        "downloaded": 0, "duplicate_id": 0, "duplicate_sha256": 0,
        "metadata_too_small": 0, "download_too_small": 0, "nonfree": 0,
        "failed": 0, "failures": [],
    }
    for query in queries:
        for page in range(1, 6):
            if stats["downloaded"] >= target:
                break
            try:
                payload = api_page(query, page)
            except Exception as exc:
                stats["failed"] += 1
                stats["failures"].append(f"API {query!r} page {page}: {type(exc).__name__}: {exc}")
                break
            results = payload.get("results") or []
            if not results:
                break
            for item in results:
                if stats["downloaded"] >= target:
                    break
                stats["api_candidates"] += 1
                item_id = normalized_id(item.get("id"))
                if not item_id or item_id in seen:
                    stats["duplicate_id"] += 1
                    continue
                seen.add(item_id)
                license_name = normalized_id(item.get("license"))
                if license_name not in ALLOWED_LICENSES or "nc" in license_name or "nd" in license_name:
                    stats["nonfree"] += 1
                    continue
                if not item.get("url") or not item.get("foreign_landing_url") or not item.get("license_url"):
                    stats["failed"] += 1
                    stats["failures"].append(f"{item_id}: missing required URL")
                    continue
                if not valid_dimensions(item.get("width"), item.get("height")):
                    stats["metadata_too_small"] += 1
                    continue
                stem = f"ov_{item_id[:8]}"
                output = class_dir / f"{stem}.jpg"
                sidecar = class_dir / f"{stem}.json"
                if output.exists() or sidecar.exists():
                    stats["duplicate_id"] += 1
                    continue
                raw_path = temp_dir / f"{class_name}_{item_id[:8]}.download"
                downloaded_from = str(item["url"])
                try:
                    raw = fetch(downloaded_from, "image/*")
                    raw_path.write_bytes(raw)
                    with Image.open(raw_path) as source:
                        source.load()
                        w, h = source.size
                        if not valid_dimensions(w, h):
                            stats["download_too_small"] += 1
                            raw_path.unlink(missing_ok=True)
                            continue
                        image = ImageOps.exif_transpose(source).convert("RGB")
                        if max(image.size) > 512:
                            image.thumbnail((512, 512), Image.Resampling.LANCZOS)
                        image.save(output, "JPEG", quality=90, optimize=True)
                    digest = sha256(output)
                    if digest in hashes:
                        stats["duplicate_sha256"] += 1
                        output.unlink(missing_ok=True)
                        raw_path.unlink(missing_ok=True)
                        continue
                    hashes.add(digest)
                    metadata = {field: item.get(field) for field in FIELDS}
                    metadata.update({
                        "our_class": class_name,
                        "local_file": output.relative_to(project).as_posix(),
                        "query": query,
                        "downloaded_from": downloaded_from,
                        "sha256": digest,
                        "stored_width": image.width,
                        "stored_height": image.height,
                        "downloaded_bytes": len(raw),
                        "review_status": "pending",
                    })
                    sidecar.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    raw_path.unlink(missing_ok=True)
                    stats["downloaded"] += 1
                    print(json.dumps({"class": class_name, "downloaded": stats["downloaded"], "file": output.name, "query": query}, ensure_ascii=False), flush=True)
                except (HTTPError, URLError, TimeoutError, OSError, UnidentifiedImageError, ValueError) as exc:
                    stats["failed"] += 1
                    stats["failures"].append(f"{item_id}: {type(exc).__name__}: {exc}")
                    output.unlink(missing_ok=True)
                    sidecar.unlink(missing_ok=True)
                    raw_path.unlink(missing_ok=True)
            if not payload.get("next"):
                break
        if stats["downloaded"] >= target:
            break
    return stats


def iter_openverse_sidecars(project: Path):
    images_root = project / "data" / "raw" / "images"
    for class_name in DEFAULT_SPECS:
        for root in (images_root / class_name, images_root / "_rejected" / class_name):
            if root.exists():
                yield from root.glob("ov_*.json")


def rebuild_provenance(project: Path) -> list[dict[str, Any]]:
    rows = []
    for sidecar in sorted(iter_openverse_sidecars(project)):
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        image = sidecar.with_suffix(".jpg")
        if not image.exists():
            continue
        data["local_file"] = image.relative_to(project).as_posix()
        data["review_status"] = "rejected" if "_rejected" in image.parts else data.get("review_status", "accepted")
        rows.append({field: data.get(field, "") for field in PROVENANCE_FIELDS})
    reports = project / "data" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "openverse_provenance.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (reports / "openverse_provenance.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PROVENANCE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def build_contact_sheets(project: Path, class_names: list[str], per_sheet: int = 25) -> list[str]:
    reports = project / "data" / "reports" / "openverse_contact_sheets"
    reports.mkdir(parents=True, exist_ok=True)
    created = []
    for class_name in class_names:
        class_dir = project / "data" / "raw" / "images" / class_name
        paths = sorted(class_dir.glob("ov_*.jpg"))
        for old in reports.glob(f"{class_name}_*.jpg"):
            old.unlink()
        for page_index, start in enumerate(range(0, len(paths), per_sheet), 1):
            page = paths[start:start + per_sheet]
            columns, cell_w, cell_h = 5, 210, 170
            rows = (len(page) + columns - 1) // columns
            sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
            draw = ImageDraw.Draw(sheet)
            for index, path in enumerate(page):
                with Image.open(path) as source:
                    thumb = ImageOps.contain(source.convert("RGB"), (cell_w - 10, cell_h - 32))
                x, y = (index % columns) * cell_w, (index // columns) * cell_h
                sheet.paste(thumb, (x + (cell_w - thumb.width) // 2, y + 3))
                draw.text((x + 5, y + cell_h - 25), path.name, fill="black")
            destination = reports / f"{class_name}_{page_index:02d}.jpg"
            sheet.save(destination, "JPEG", quality=90)
            created.append(destination.relative_to(project).as_posix())
    return created


def build_review_contact_sheets(project: Path, class_names: list[str], per_sheet: int = 25) -> list[str]:
    """Build immutable review sheets containing accepted and rejected images."""
    images_root = project / "data" / "raw" / "images"
    destination_root = project / "data" / "reports" / "openverse_contact_sheets_reviewed"
    destination_root.mkdir(parents=True, exist_ok=True)
    created = []
    for class_name in class_names:
        accepted = list((images_root / class_name).glob("ov_*.jpg"))
        rejected = list((images_root / "_rejected" / class_name).glob("ov_*.jpg"))
        paths = sorted([*accepted, *rejected], key=lambda path: path.name)
        for old in destination_root.glob(f"{class_name}_*.jpg"):
            old.unlink()
        for page_index, start in enumerate(range(0, len(paths), per_sheet), 1):
            page = paths[start:start + per_sheet]
            columns, cell_w, cell_h = 5, 210, 174
            rows = (len(page) + columns - 1) // columns
            sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
            draw = ImageDraw.Draw(sheet)
            for index, path in enumerate(page):
                is_rejected = "_rejected" in path.parts
                with Image.open(path) as source:
                    thumb = ImageOps.contain(source.convert("RGB"), (cell_w - 12, cell_h - 38))
                x, y = (index % columns) * cell_w, (index // columns) * cell_h
                sheet.paste(thumb, (x + (cell_w - thumb.width) // 2, y + 4))
                color = "#b00020" if is_rejected else "#087f23"
                label = ("LOAI " if is_rejected else "GIU  ") + path.name
                draw.rectangle((x + 1, y + 1, x + cell_w - 2, y + cell_h - 2), outline=color, width=3)
                draw.text((x + 5, y + cell_h - 29), label, fill=color)
            destination = destination_root / f"{class_name}_{page_index:02d}.jpg"
            sheet.save(destination, "JPEG", quality=90)
            created.append(destination.relative_to(project).as_posix())
    return created


def reject_images(project: Path, decisions_path: Path) -> int:
    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
    review_path = project / "data" / "reports" / "openverse_visual_review.json"
    existing = []
    if review_path.exists():
        existing = json.loads(review_path.read_text(encoding="utf-8"))
    by_key = {
        (row.get("class") or row["lớp"], row.get("file") or row["tên file"]): row
        for row in existing
    }
    moved = 0
    for row in decisions:
        class_name, filename = row["class"], row["file"]
        conclusion = row.get("conclusion", "rejected")
        if conclusion != "rejected":
            continue
        source = project / "data" / "raw" / "images" / class_name / filename
        destination_dir = project / "data" / "raw" / "images" / "_rejected" / class_name
        destination_dir.mkdir(parents=True, exist_ok=True)
        recorded_rejection = source.exists() or (destination_dir / filename).exists()
        if source.exists():
            shutil.move(str(source), destination_dir / source.name)
            source_sidecar = source.with_suffix(".json")
            if source_sidecar.exists():
                shutil.move(str(source_sidecar), destination_dir / source_sidecar.name)
            moved += 1
        if recorded_rejection:
            by_key[(class_name, filename)] = {
                "lớp": class_name, "tên file": filename, "kết luận": "loại", "lý do": row["reason"]
            }
    review = sorted(
        ({
            "lớp": row.get("lớp") or row["class"],
            "tên file": row.get("tên file") or row["file"],
            "kết luận": row.get("kết luận") or ("loại" if row.get("conclusion") == "rejected" else row.get("conclusion", "")),
            "lý do": row.get("lý do") or row.get("reason", ""),
        } for row in by_key.values()),
        key=lambda row: (row["lớp"], row["tên file"]),
    )
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return moved


def parse_args() -> argparse.Namespace:
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=project)
    parser.add_argument("--classes", nargs="*", choices=sorted(DEFAULT_SPECS), default=list(DEFAULT_SPECS))
    parser.add_argument("--target", action="append", default=[], metavar="CLASS=N")
    parser.add_argument("--reports-only", action="store_true")
    parser.add_argument("--reject-from", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = args.project.resolve()
    targets = dict(DEFAULT_TARGETS)
    for spec in args.target:
        name, value = spec.split("=", 1)
        targets[name] = int(value)
    if args.reject_from:
        moved = reject_images(project, args.reject_from)
        print(json.dumps({"moved": moved}, ensure_ascii=False))
    summaries = []
    if not args.reports_only and not args.reject_from:
        for class_name in args.classes:
            summaries.append(collect_class(project, class_name, DEFAULT_SPECS[class_name], targets[class_name]))
            print(json.dumps(summaries[-1], ensure_ascii=False), flush=True)
        reports = project / "data" / "reports"
        (reports / "openverse_collection_stats.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = rebuild_provenance(project)
    sheets = build_contact_sheets(project, args.classes)
    reviewed_sheets = build_review_contact_sheets(project, args.classes)
    print(json.dumps({"provenance_rows": len(rows), "contact_sheets": sheets, "reviewed_contact_sheets": reviewed_sheets}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
