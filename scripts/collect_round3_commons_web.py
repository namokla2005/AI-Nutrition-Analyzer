#!/usr/bin/env python3
"""Supplement round-3 classes from Commons, then Bing image search.

Commons records retain explicit license metadata. Bing is used only when the
freely licensed sources do not reach the requested count; its records keep the
real image and landing-page URLs and leave unknown license fields null.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import time
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT / "data" / "raw" / "images"
SHEETS = PROJECT / "data" / "reports" / "round3_contact_sheets"
COMMONS = "https://commons.wikimedia.org/w/api.php"
UA = "AI-Nutrition-Analyzer-Round3/1.0 (academic dataset; contact: https://github.com/namokla2005/AI-Nutrition-Analyzer)"
TARGET = 160
MIN_BYTES = 5 * 1024
QUERIES = {
    "goi_ga": ["chicken cabbage salad bowl recipe", "shredded chicken salad bowl", "Asian chicken salad dish"],
    "banh_trang_nuong": ["rice paper pizza banh trang nuong", "grilled rice paper pizza food"],
    "mi_xao": ["stir fried noodles plate food", "stir fried egg noodles dish", "seafood stir fried noodles plate"],
}
ALLOWED = ("cc0", "cc by", "public domain")


def safe_text(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("value", "")
    return re.sub(r"<[^>]+>", "", html.unescape(str(value or ""))).strip()


def normalize(raw: bytes) -> tuple[bytes, int, int]:
    if len(raw) < MIN_BYTES:
        raise ValueError("under 5 KB")
    with Image.open(BytesIO(raw)) as source:
        source.load()
        image = ImageOps.exif_transpose(source).convert("RGB")
    if min(image.size) < 180 or max(image.size) < 300:
        raise ValueError("dimensions too small")
    if max(image.size) > 768:
        image.thumbnail((768, 768), Image.Resampling.LANCZOS)
    output = BytesIO()
    image.save(output, "JPEG", quality=91, optimize=True)
    data = output.getvalue()
    if len(data) < MIN_BYTES:
        raise ValueError("normalized image under 5 KB")
    return data, image.width, image.height


def hashes(folder: Path) -> set[str]:
    found = set()
    for path in folder.glob("*.jpg"):
        try:
            found.add(hashlib.sha256(path.read_bytes()).hexdigest())
        except OSError:
            pass
    return found


def get_bytes(client: httpx.Client, url: str, referer: str = "") -> bytes:
    response = client.get(url, headers={"Referer": referer} if referer else {}, timeout=45, follow_redirects=True)
    response.raise_for_status()
    ctype = response.headers.get("content-type", "").lower()
    if "image" not in ctype and not re.search(r"\.(jpe?g|png|webp)(?:\?|$)", str(response.url), re.I):
        raise ValueError("not an image response")
    return response.content


def commons_candidates(client: httpx.Client, query: str) -> list[dict[str, Any]]:
    params = {
        "action": "query", "format": "json", "formatversion": "2",
        "generator": "search", "gsrsearch": f'"{query}" filetype:bitmap',
        "gsrnamespace": "6", "gsrlimit": "100", "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
    }
    response = client.get(COMMONS, params=params, timeout=60)
    response.raise_for_status()
    time.sleep(1)
    return (response.json().get("query") or {}).get("pages") or []


def collect_commons(client: httpx.Client, class_name: str, folder: Path, seen_hashes: set[str]) -> int:
    added = 0
    known = {p.stem for p in folder.glob("commons_*.jpg")}
    for query in QUERIES[class_name]:
        for page in commons_candidates(client, query):
            pageid = str(page.get("pageid") or "")
            stem = f"commons_{pageid}"
            if not pageid or stem in known:
                continue
            info = ((page.get("imageinfo") or [{}])[0])
            ext = info.get("extmetadata") or {}
            license_name = safe_text(ext.get("LicenseShortName"))
            if not any(token in license_name.lower() for token in ALLOWED) or "nc" in license_name.lower() or "nd" in license_name.lower():
                continue
            url = str(info.get("url") or "")
            landing = str(info.get("descriptionurl") or "")
            if not url or not landing:
                continue
            try:
                jpeg, width, height = normalize(get_bytes(client, url, landing))
                time.sleep(1)
                sha = hashlib.sha256(jpeg).hexdigest()
                if sha in seen_hashes:
                    continue
                seen_hashes.add(sha)
                image = folder / f"{stem}.jpg"
                sidecar = folder / f"{stem}.json"
                image.write_bytes(jpeg)
                record = {
                    "id": pageid, "title": page.get("title"), "url": url,
                    "foreign_landing_url": landing,
                    "creator": safe_text(ext.get("Artist") or ext.get("Credit")),
                    "license": license_name,
                    "license_url": safe_text(ext.get("LicenseUrl")),
                    "provider": "Wikimedia Commons", "source": "commons",
                    "width": width, "height": height, "sha256": sha,
                    "our_class": class_name, "query": query, "review_status": "pending",
                }
                sidecar.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                known.add(stem)
                added += 1
                print(json.dumps({"class": class_name, "source": "commons", "file": image.name}, ensure_ascii=False), flush=True)
            except (httpx.HTTPError, OSError, ValueError, UnidentifiedImageError):
                continue
    return added


def bing_candidates(client: httpx.Client, query: str, first: int) -> list[dict[str, str]]:
    url = f"https://www.bing.com/images/search?q={quote_plus(query)}&form=HDRSC3&first={first}&count=35"
    response = client.get(url, timeout=60, follow_redirects=True)
    response.raise_for_status()
    time.sleep(1)
    results = []
    for raw in re.findall(r'\bm="([^"]+)"', response.text):
        try:
            data = json.loads(html.unescape(raw))
        except (ValueError, TypeError):
            continue
        image_url = str(data.get("murl") or "")
        landing = str(data.get("purl") or "")
        if image_url and landing:
            results.append({"url": image_url, "landing": landing, "title": str(data.get("t") or "")})
    return results


def collect_web(client: httpx.Client, class_name: str, folder: Path, seen_hashes: set[str]) -> int:
    added = 0
    known_urls = set()
    for sidecar in folder.glob("web_*.json"):
        try:
            known_urls.add(str(json.loads(sidecar.read_text(encoding="utf-8")).get("url", "")))
        except (OSError, json.JSONDecodeError):
            pass
    for query in QUERIES[class_name]:
        for first in (1, 36, 71, 106):
            if len(list(folder.glob("*.jpg"))) >= TARGET:
                return added
            for item in bing_candidates(client, query, first):
                if len(list(folder.glob("*.jpg"))) >= TARGET:
                    return added
                url, landing = item["url"], item["landing"]
                if url in known_urls:
                    continue
                known_urls.add(url)
                try:
                    jpeg, width, height = normalize(get_bytes(client, url, landing))
                    time.sleep(1)
                    sha = hashlib.sha256(jpeg).hexdigest()
                    if sha in seen_hashes:
                        continue
                    seen_hashes.add(sha)
                    short = hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
                    stem = f"web_{short}"
                    if (folder / f"{stem}.jpg").exists():
                        continue
                    (folder / f"{stem}.jpg").write_bytes(jpeg)
                    record = {
                        "id": short, "title": item["title"], "url": url,
                        "foreign_landing_url": landing, "creator": None,
                        "license": None, "license_url": None, "provider": "Bing Images",
                        "source": "web", "width": width, "height": height,
                        "sha256": sha, "our_class": class_name, "query": query,
                        "review_status": "pending",
                    }
                    (folder / f"{stem}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    added += 1
                    print(json.dumps({"class": class_name, "source": "web", "file": f"{stem}.jpg", "count": len(list(folder.glob('*.jpg')))}, ensure_ascii=False), flush=True)
                except (httpx.HTTPError, OSError, ValueError, UnidentifiedImageError):
                    continue
    return added


def build_sheets() -> list[str]:
    SHEETS.mkdir(parents=True, exist_ok=True)
    created = []
    for class_name in QUERIES:
        for old in SHEETS.glob(f"{class_name}_*.jpg"):
            old.unlink()
        paths = sorted((ROOT / class_name).glob("*.jpg"))
        for page_no, start in enumerate(range(0, len(paths), 25), 1):
            page = paths[start:start + 25]
            cw, ch, cols = 220, 175, 5
            rows = (len(page) + cols - 1) // cols
            sheet = Image.new("RGB", (cols * cw, rows * ch), "white")
            draw = ImageDraw.Draw(sheet)
            for i, path in enumerate(page):
                with Image.open(path) as src:
                    thumb = ImageOps.contain(src.convert("RGB"), (cw - 10, ch - 36))
                x, y = i % cols * cw, i // cols * ch
                sheet.paste(thumb, (x + (cw - thumb.width) // 2, y + 3))
                draw.text((x + 5, y + ch - 30), f"{start+i+1:03d} {path.name}", fill="black")
            out = SHEETS / f"{class_name}_{page_no:02d}.jpg"
            sheet.save(out, "JPEG", quality=92)
            created.append(out.relative_to(PROJECT).as_posix())
    return created


def main() -> int:
    summary = []
    with httpx.Client(headers={"User-Agent": UA, "Accept": "*/*"}) as client:
        for class_name in QUERIES:
            folder = ROOT / class_name
            folder.mkdir(parents=True, exist_ok=True)
            seen = hashes(folder)
            before = len(list(folder.glob("*.jpg")))
            commons = collect_commons(client, class_name, folder, seen)
            web = collect_web(client, class_name, folder, seen)
            after = len(list(folder.glob("*.jpg")))
            summary.append({"class": class_name, "before": before, "commons_new": commons, "web_new": web, "total": after})
    sheets = build_sheets()
    report = {"target": TARGET, "classes": summary, "contact_sheets": sheets}
    path = PROJECT / "data" / "reports" / "round3_supplement_stats.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
