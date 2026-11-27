#!/usr/bin/env python3
"""Collect round-3 images for four new Vietnamese food classes.

Uses Openverse first, then Wikimedia Commons. Creates JPEGs, JSON sidecars,
and numbered contact sheets. Visual decisions are applied separately.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT / "data" / "raw" / "images"
REPORTS = PROJECT / "data" / "reports"
UA = "AI-Nutrition-Analyzer/round3 academic image collection (contact: namokla2005)"
LICENSES = {"cc0", "by", "by-sa"}
SPECS = {
    "ca_kho_to": [
        "cá kho tộ", "ca kho to", "Vietnamese braised fish clay pot",
        "Vietnamese caramelized fish", "caramelized fish clay pot", "cá kho",
    ],
    "com_ga": [
        "cơm gà", "com ga", "Vietnamese chicken rice", "Hoi An chicken rice",
        "cơm gà hải nam", "Hainanese chicken rice",
    ],
    "xoi_xeo": [
        "xôi xéo", "xoi xeo", "Vietnamese sticky rice mung bean",
        "Vietnamese yellow sticky rice", "sticky rice mung bean Vietnamese",
    ],
    "che_ba_mau": [
        "chè ba màu", "che ba mau", "Vietnamese three color dessert",
        "Vietnamese three colour dessert", "Vietnamese rainbow dessert",
        "three color dessert",
    ],
}
MIN_BYTES = 5 * 1024
TARGET = 60
_last_download = 0.0


def download_paced(client: httpx.Client, urls: list[str], referer: str = "") -> tuple[bytes, str]:
    global _last_download
    for url in urls:
        if not url:
            continue
        delay = 1.02 - (time.monotonic() - _last_download)
        if delay > 0:
            time.sleep(delay)
        try:
            headers = {"Accept": "image/*"}
            if referer:
                headers["Referer"] = referer
            response = client.get(url, headers=headers, follow_redirects=True)
            _last_download = time.monotonic()
            response.raise_for_status()
            data = response.content
            if len(data) < MIN_BYTES:
                continue
            ctype = response.headers.get("content-type", "").lower()
            if "image" not in ctype and not data.startswith((b"\xff\xd8", b"\x89PNG", b"GIF8", b"RIFF")):
                continue
            return data, str(response.url)
        except (httpx.HTTPError, OSError):
            _last_download = time.monotonic()
    raise ValueError("all image URLs failed")


def image_to_jpeg(data: bytes) -> tuple[bytes, int, int]:
    try:
        with Image.open(io.BytesIO(data)) as source:
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("not a real image") from exc
    if min(image.size) < 200 or max(image.size) < 300:
        raise ValueError("image dimensions too small")
    if max(image.size) > 768:
        image.thumbnail((768, 768), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    image.save(out, "JPEG", quality=91, optimize=True)
    payload = out.getvalue()
    if len(payload) < MIN_BYTES:
        raise ValueError("stored JPEG below 5 KB")
    return payload, image.width, image.height


def existing_state(class_name: str) -> tuple[set[str], set[str]]:
    ids: set[str] = set()
    hashes: set[str] = set()
    for base in (ROOT / class_name, ROOT / "_rejected" / class_name):
        if not base.exists():
            continue
        for sidecar in base.glob("*.json"):
            try:
                ids.add(str(json.loads(sidecar.read_text(encoding="utf-8")).get("id", "")))
            except (OSError, json.JSONDecodeError):
                pass
        for image in base.glob("*.jpg"):
            hashes.add(hashlib.sha256(image.read_bytes()).hexdigest())
    return ids, hashes


def unique_stem(class_dir: Path, prefix: str, token: str) -> str:
    stem = f"{prefix}_{token}"
    if not (class_dir / f"{stem}.jpg").exists() and not (class_dir / f"{stem}.json").exists():
        return stem
    n = 2
    while (class_dir / f"{stem}_{n}.jpg").exists() or (class_dir / f"{stem}_{n}.json").exists():
        n += 1
    return f"{stem}_{n}"


def save_item(class_name: str, prefix: str, token: str, item: dict[str, Any], query: str,
              data: bytes, downloaded_from: str, hashes: set[str]) -> bool:
    payload, stored_w, stored_h = image_to_jpeg(data)
    digest = hashlib.sha256(payload).hexdigest()
    if digest in hashes:
        return False
    class_dir = ROOT / class_name
    class_dir.mkdir(parents=True, exist_ok=True)
    stem = unique_stem(class_dir, prefix, token)
    image_path = class_dir / f"{stem}.jpg"
    sidecar_path = class_dir / f"{stem}.json"
    metadata = {
        "id": str(item.get("id", "")),
        "title": item.get("title") or "",
        "url": item.get("url") or "",
        "foreign_landing_url": item.get("foreign_landing_url") or "",
        "creator": item.get("creator") or "",
        "license": item.get("license") or "",
        "license_url": item.get("license_url") or "",
        "provider": item.get("provider") or "",
        "source": item.get("source") or "",
        "width": item.get("width") or stored_w,
        "height": item.get("height") or stored_h,
        "sha256": digest,
        "our_class": class_name,
        "query": query,
        "local_file": image_path.relative_to(PROJECT).as_posix(),
        "downloaded_from": downloaded_from,
        "stored_width": stored_w,
        "stored_height": stored_h,
        "downloaded_bytes": len(data),
        "review_status": "pending",
    }
    image_path.write_bytes(payload)
    sidecar_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    hashes.add(digest)
    return True


def collect_openverse(client: httpx.Client, class_name: str, queries: list[str], target: int,
                       ids: set[str], hashes: set[str]) -> dict[str, int]:
    stats = {"candidates": 0, "saved": 0, "failed": 0, "duplicates": 0}
    for query in queries:
        for page in range(1, 8):
            if stats["saved"] >= target:
                return stats
            params = {"q": query, "page_size": 20, "page": page, "license": "cc0,by,by-sa"}
            try:
                response = client.get("https://api.openverse.org/v1/images/", params=params)
                response.raise_for_status()
                result = response.json()
            except (httpx.HTTPError, ValueError):
                stats["failed"] += 1
                break
            rows = result.get("results") or []
            if not rows:
                break
            for item in rows:
                if stats["saved"] >= target:
                    return stats
                stats["candidates"] += 1
                item_id = str(item.get("id") or "").lower()
                if not item_id or item_id in ids:
                    stats["duplicates"] += 1
                    continue
                ids.add(item_id)
                license_name = str(item.get("license") or "").lower()
                if license_name not in LICENSES:
                    continue
                try:
                    data, downloaded_from = download_paced(
                        client, [str(item.get("url") or ""), str(item.get("thumbnail") or "")],
                        str(item.get("foreign_landing_url") or ""),
                    )
                    if save_item(class_name, "ov", item_id[:8], item, query, data, downloaded_from, hashes):
                        stats["saved"] += 1
                        print(json.dumps({"class": class_name, "source": "openverse", "saved": stats["saved"], "file": f"ov_{item_id[:8]}.jpg", "query": query}, ensure_ascii=False), flush=True)
                    else:
                        stats["duplicates"] += 1
                except (ValueError, OSError):
                    stats["failed"] += 1
            if not result.get("next"):
                break
    return stats


def commons_license(meta: dict[str, Any]) -> tuple[str, str]:
    short = str((meta.get("LicenseShortName") or {}).get("value") or "")
    url = str((meta.get("LicenseUrl") or {}).get("value") or "")
    low = short.lower()
    if "public domain" in low:
        return "cc0", url
    if "cc by-sa" in low:
        return "by-sa", url
    if "cc by" in low:
        return "by", url
    return "", url


def collect_commons(client: httpx.Client, class_name: str, queries: list[str], needed: int,
                    ids: set[str], hashes: set[str]) -> dict[str, int]:
    stats = {"candidates": 0, "saved": 0, "failed": 0, "duplicates": 0}
    for query in queries:
        if stats["saved"] >= needed:
            break
        params = {
            "action": "query", "format": "json", "formatversion": 2,
            "generator": "search", "gsrsearch": f'"{query}" filetype:bitmap',
            "gsrnamespace": 6, "gsrlimit": 50, "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
        }
        try:
            response = client.get("https://commons.wikimedia.org/w/api.php", params=params)
            response.raise_for_status()
            pages = (response.json().get("query") or {}).get("pages") or []
        except (httpx.HTTPError, ValueError):
            stats["failed"] += 1
            continue
        for page in pages:
            if stats["saved"] >= needed:
                break
            stats["candidates"] += 1
            pageid = str(page.get("pageid") or "")
            item_id = f"commons:{pageid}"
            if not pageid or item_id in ids:
                stats["duplicates"] += 1
                continue
            ids.add(item_id)
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            license_name, license_url = commons_license(meta)
            if not license_name:
                continue
            url = str(info.get("url") or "")
            item = {
                "id": pageid,
                "title": page.get("title") or "",
                "url": url,
                "foreign_landing_url": str(info.get("descriptionurl") or ""),
                "creator": str((meta.get("Artist") or {}).get("value") or ""),
                "license": license_name,
                "license_url": license_url,
                "provider": "wikimedia",
                "source": "wikimedia_commons",
                "width": info.get("width"),
                "height": info.get("height"),
            }
            try:
                data, downloaded_from = download_paced(client, [url], item["foreign_landing_url"])
                if save_item(class_name, "commons", pageid, item, query, data, downloaded_from, hashes):
                    stats["saved"] += 1
                    print(json.dumps({"class": class_name, "source": "commons", "saved": stats["saved"], "file": f"commons_{pageid}.jpg", "query": query}, ensure_ascii=False), flush=True)
                else:
                    stats["duplicates"] += 1
            except (ValueError, OSError):
                stats["failed"] += 1
        time.sleep(1.0)
    return stats


def build_contact_sheets(classes: list[str], per_sheet: int = 25) -> list[str]:
    out_dir = REPORTS / "round3_contact_sheets"
    out_dir.mkdir(parents=True, exist_ok=True)
    made: list[str] = []
    for class_name in classes:
        for old in out_dir.glob(f"{class_name}_*.jpg"):
            old.unlink()
        paths = sorted((ROOT / class_name).glob("*.jpg"))
        for page_no, start in enumerate(range(0, len(paths), per_sheet), 1):
            batch = paths[start:start + per_sheet]
            cw, ch, cols = 220, 180, 5
            rows = (len(batch) + cols - 1) // cols
            sheet = Image.new("RGB", (cw * cols, ch * rows), "white")
            draw = ImageDraw.Draw(sheet)
            for local_idx, path in enumerate(batch):
                with Image.open(path) as source:
                    thumb = ImageOps.contain(source.convert("RGB"), (cw - 10, ch - 42))
                x, y = (local_idx % cols) * cw, (local_idx // cols) * ch
                sheet.paste(thumb, (x + (cw - thumb.width) // 2, y + 3))
                absolute_idx = start + local_idx + 1
                draw.text((x + 5, y + ch - 36), f"{absolute_idx:03d} {path.name}", fill="black")
            dest = out_dir / f"{class_name}_{page_no:02d}.jpg"
            sheet.save(dest, "JPEG", quality=92)
            made.append(dest.relative_to(PROJECT).as_posix())
    return made


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--classes", nargs="*", choices=sorted(SPECS), default=list(SPECS))
    parser.add_argument("--target", type=int, default=TARGET)
    parser.add_argument("--sheets-only", action="store_true")
    args = parser.parse_args()
    REPORTS.mkdir(parents=True, exist_ok=True)
    summaries = []
    if not args.sheets_only:
        with httpx.Client(headers={"User-Agent": UA}, timeout=httpx.Timeout(35.0, connect=15.0)) as client:
            for class_name in args.classes:
                (ROOT / class_name).mkdir(parents=True, exist_ok=True)
                ids, hashes = existing_state(class_name)
                existing = len(list((ROOT / class_name).glob("*.jpg")))
                openverse = collect_openverse(client, class_name, SPECS[class_name], max(0, args.target - existing), ids, hashes)
                now = len(list((ROOT / class_name).glob("*.jpg")))
                commons = collect_commons(client, class_name, SPECS[class_name], max(0, args.target - now), ids, hashes)
                final = len(list((ROOT / class_name).glob("*.jpg")))
                summaries.append({"class": class_name, "before": existing, "openverse": openverse, "commons": commons, "downloaded_total": final})
                print(json.dumps(summaries[-1], ensure_ascii=False), flush=True)
        (REPORTS / "round3_collection_stats.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sheets = build_contact_sheets(args.classes)
    print(json.dumps({"contact_sheets": sheets}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
