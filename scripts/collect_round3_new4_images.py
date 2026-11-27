#!/usr/bin/env python3
"""Collect round-3 images for four new Vietnamese-food classes.

Uses Openverse only in the collection phase. Every image is normalized to JPEG,
paired with a JSON sidecar, deduplicated by SHA-256, and included in numbered
contact sheets. Visual decisions and final provenance are handled by the
companion review script.
"""
from __future__ import annotations

import hashlib
import json
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT / "data" / "raw" / "images"
SHEETS = PROJECT / "data" / "reports" / "round3_contact_sheets"
API = "https://api.openverse.org/v1/images/"
UA = "AI-Nutrition-Analyzer/round3 academic image collector"
TARGET = 55
MIN_BYTES = 5 * 1024
QUERIES = {
    "banh_da_cua": [
        "bánh đa cua", "banh da cua", "bánh đa cua Hải Phòng",
        "banh da cua Hai Phong", "Hai Phong crab noodle soup",
        "Vietnamese red rice noodle crab soup",
    ],
    "goi_ga": [
        "gỏi gà", "goi ga", "Vietnamese chicken salad",
        "Vietnamese shredded chicken salad", "Vietnamese cabbage chicken salad",
        "Vietnamese banana blossom chicken salad",
    ],
    "banh_trang_nuong": [
        "bánh tráng nướng", "banh trang nuong", "Vietnamese pizza",
        "Vietnamese grilled rice paper", "Dalat grilled rice paper",
        "Da Lat pizza rice paper",
    ],
    "mi_xao": [
        "mì xào", "mi xao", "Vietnamese stir fried noodles",
        "Vietnamese fried noodles", "stir fried egg noodles Vietnam",
        "Vietnamese seafood fried noodles",
    ],
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def image_hashes(folder: Path) -> set[str]:
    values: set[str] = set()
    for path in folder.glob("*.jpg"):
        try:
            values.add(hashlib.sha256(path.read_bytes()).hexdigest())
        except OSError:
            pass
    return values


def fetch_json(client: httpx.Client, query: str, page: int) -> dict[str, Any]:
    params = {
        "q": query,
        "page_size": 20,
        "page": page,
        "license": "cc0,by,by-sa",
        "license_type": "commercial,modification",
    }
    for attempt in range(5):
        try:
            response = client.get(API, params=params, timeout=60)
            if response.status_code == 429:
                time.sleep(2 ** (attempt + 1))
                continue
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            if attempt == 4:
                raise
            time.sleep(2 ** (attempt + 1))
    raise AssertionError("unreachable")


def fetch_image(client: httpx.Client, urls: list[str], referer: str) -> tuple[bytes, str]:
    for url in urls:
        if not url:
            continue
        for attempt in range(2):
            try:
                response = client.get(url, headers={"Referer": referer}, timeout=60, follow_redirects=True)
                response.raise_for_status()
                content = response.content
                if len(content) < MIN_BYTES:
                    break
                with Image.open(BytesIO(content)) as image:
                    image.verify()
                return content, str(response.url)
            except (httpx.HTTPError, UnidentifiedImageError, OSError, ValueError):
                if attempt == 0:
                    time.sleep(1)
    raise ValueError("all image URLs failed or were smaller than 5 KB")


def stored_jpeg(raw: bytes) -> tuple[bytes, int, int]:
    with Image.open(BytesIO(raw)) as source:
        source.load()
        image = ImageOps.exif_transpose(source).convert("RGB")
    if min(image.size) < 180 or max(image.size) < 300:
        raise ValueError("image dimensions too small")
    if max(image.size) > 768:
        image.thumbnail((768, 768), Image.Resampling.LANCZOS)
    output = BytesIO()
    image.save(output, "JPEG", quality=91, optimize=True)
    data = output.getvalue()
    if len(data) < MIN_BYTES:
        raise ValueError("normalized JPEG smaller than 5 KB")
    return data, image.width, image.height


def collect_one(client: httpx.Client, class_name: str) -> dict[str, Any]:
    folder = ROOT / class_name
    folder.mkdir(parents=True, exist_ok=True)
    (ROOT / "_rejected" / class_name).mkdir(parents=True, exist_ok=True)
    hashes = image_hashes(folder)
    known_ids = set()
    for sidecar in [*folder.glob("*.json"), *(ROOT / "_rejected" / class_name).glob("*.json")]:
        try:
            known_ids.add(str(json.loads(sidecar.read_text(encoding="utf-8")).get("id", "")))
        except (OSError, json.JSONDecodeError):
            pass
    downloaded = len(list(folder.glob("*.jpg")))
    start_count = downloaded
    failures = 0
    for query in QUERIES[class_name]:
        if downloaded >= TARGET:
            break
        for page in range(1, 8):
            if downloaded >= TARGET:
                break
            payload = fetch_json(client, query, page)
            time.sleep(1.0)
            results = payload.get("results") or []
            if not results:
                break
            for item in results:
                if downloaded >= TARGET:
                    break
                item_id = str(item.get("id") or "").lower()
                if not item_id or item_id in known_ids:
                    continue
                known_ids.add(item_id)
                license_name = str(item.get("license") or "").lower()
                if license_name not in {"cc0", "by", "by-sa"}:
                    continue
                landing = str(item.get("foreign_landing_url") or "")
                if not landing or not item.get("license_url"):
                    continue
                try:
                    raw, downloaded_from = fetch_image(
                        client,
                        [str(item.get("url") or ""), str(item.get("thumbnail") or "")],
                        landing,
                    )
                    time.sleep(1.0)
                    jpeg, width, height = stored_jpeg(raw)
                    sha = digest(jpeg)
                    if sha in hashes:
                        continue
                    hashes.add(sha)
                    stem = f"ov_{item_id[:8]}"
                    image_path = folder / f"{stem}.jpg"
                    sidecar_path = folder / f"{stem}.json"
                    if image_path.exists() or sidecar_path.exists():
                        continue
                    image_path.write_bytes(jpeg)
                    metadata = {
                        "id": item_id,
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "foreign_landing_url": landing,
                        "creator": item.get("creator"),
                        "license": license_name,
                        "license_url": item.get("license_url"),
                        "provider": item.get("provider"),
                        "source": item.get("source"),
                        "width": width,
                        "height": height,
                        "sha256": sha,
                        "our_class": class_name,
                        "query": query,
                        "downloaded_from": downloaded_from,
                        "review_status": "pending",
                    }
                    sidecar_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    downloaded += 1
                    print(json.dumps({"class": class_name, "count": downloaded, "file": image_path.name, "query": query}, ensure_ascii=False), flush=True)
                except Exception as exc:
                    failures += 1
                    print(json.dumps({"warning": type(exc).__name__, "id": item_id, "message": str(exc)[:160]}), flush=True)
            if not payload.get("next"):
                break
    return {"class": class_name, "downloaded_new": downloaded - start_count, "total": downloaded, "failures": failures}


def build_sheets() -> list[str]:
    SHEETS.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    for class_name in QUERIES:
        for old in SHEETS.glob(f"{class_name}_*.jpg"):
            old.unlink()
        paths = sorted((ROOT / class_name).glob("*.jpg"))
        for page_no, start in enumerate(range(0, len(paths), 25), 1):
            page = paths[start:start + 25]
            cell_w, cell_h, cols = 220, 175, 5
            rows = (len(page) + cols - 1) // cols
            sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
            draw = ImageDraw.Draw(sheet)
            for index, path in enumerate(page):
                with Image.open(path) as source:
                    thumb = ImageOps.contain(source.convert("RGB"), (cell_w - 10, cell_h - 36))
                x, y = index % cols * cell_w, index // cols * cell_h
                sheet.paste(thumb, (x + (cell_w - thumb.width) // 2, y + 3))
                draw.text((x + 5, y + cell_h - 30), f"{start + index + 1:03d} {path.name}", fill="black")
            out = SHEETS / f"{class_name}_{page_no:02d}.jpg"
            sheet.save(out, "JPEG", quality=92)
            created.append(out.relative_to(PROJECT).as_posix())
    return created


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    summaries = []
    with httpx.Client(headers={"User-Agent": UA, "Accept": "*/*"}) as client:
        for class_name in QUERIES:
            summaries.append(collect_one(client, class_name))
    sheets = build_sheets()
    report = {"target_per_class": TARGET, "classes": summaries, "contact_sheets": sheets}
    path = PROJECT / "data" / "reports" / "round3_collection_stats.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
