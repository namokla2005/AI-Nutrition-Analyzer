#!/usr/bin/env python3
"""Collect freely reusable Vietnamese-food images from Wikimedia Commons.

Uses only Python's standard library and the public MediaWiki API.  The default
output is data/raw/images/<class>/ relative to the project root.  Every image
has a same-stem .json sidecar containing its Commons provenance and licence.
"""

from __future__ import annotations

import argparse
import html
import json
import mimetypes
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = (
    "AI-Nutrition-Analyzer-Commons-Collector/1.0 "
    "(academic dataset sourcing; https://commons.wikimedia.org/)"
)
DEFAULT_CATEGORIES = [
    "Phở",
    "Bánh mì",
    "Bún bò Huế",
    "Cơm tấm",
    "Bánh xèo",
    "Bún chả",
    "Gỏi cuốn",
]
FREE_LICENCE_RE = re.compile(
    r"^(?:CC0(?: \d\.\d)?|CC BY(?:-SA)? \d\.\d|Public domain|PDM)$",
    re.IGNORECASE,
)
INVALID_WINDOWS_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
TAG_RE = re.compile(r"<[^>]+>")


def api_get(params: dict[str, Any], retries: int = 3) -> dict[str, Any]:
    """GET and decode one MediaWiki API response with bounded retries."""
    query = {"format": "json", "formatversion": "2", **params}
    url = f"{API_URL}?{urlencode(query)}"
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=60) as response:
                if response.status != 200:
                    raise RuntimeError(f"MediaWiki API returned HTTP {response.status}: {url}")
                return json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt + 1 == retries:
                raise RuntimeError(f"MediaWiki API request failed after {retries} attempts: {exc}") from exc
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def clean_text(value: str | None) -> str:
    """Turn Commons extmetadata HTML fragments into plain text."""
    if not value:
        return ""
    return html.unescape(TAG_RE.sub("", value)).strip()


def is_reusable(licence: str, copyright_status: str) -> bool:
    """Accept only CC0, CC-BY, CC-BY-SA and public-domain files.

    Commons marks CC-BY/CC-BY-SA works as ``Copyrighted=True`` because the
    author retains copyright; that flag does not make the stated free licence
    non-reusable.  Keep the argument for provenance clarity but decide from the
    allow-listed licence name only.
    """
    del copyright_status
    return bool(FREE_LICENCE_RE.fullmatch(licence.strip()))


def category_title(category: str) -> str:
    category = category.strip()
    return category if category.lower().startswith("category:") else f"Category:{category}"


def class_directory_name(category: str) -> str:
    """Make a readable Windows-safe class directory name."""
    name = category_title(category).split(":", 1)[1].strip().rstrip(". ")
    name = INVALID_WINDOWS_CHARS_RE.sub("_", name)
    return name or "unnamed_category"


def safe_stem(title: str, pageid: int) -> str:
    name = title.split(":", 1)[-1]
    name = unicodedata.normalize("NFC", Path(name).stem)
    name = INVALID_WINDOWS_CHARS_RE.sub("_", name).strip().rstrip(". ")
    name = re.sub(r"\s+", " ", name)[:140].rstrip(". ")
    return f"{pageid}_{name or 'image'}"


def iter_category_files(category: str) -> Iterator[dict[str, Any]]:
    """Yield direct file members and image metadata for a Commons category."""
    continuation: dict[str, Any] = {}
    while True:
        payload = api_get(
            {
                "action": "query",
                "generator": "categorymembers",
                "gcmtitle": category_title(category),
                "gcmtype": "file",
                "gcmlimit": "max",
                "prop": "imageinfo",
                "iiprop": "url|mime|size|extmetadata",
                "iiurlwidth": "1600",
                **continuation,
            }
        )
        for page in payload.get("query", {}).get("pages", []):
            if not page.get("missing") and page.get("imageinfo"):
                yield page
        if "continue" not in payload:
            break
        continuation = payload["continue"]


def metadata_from_page(page: dict[str, Any], category: str) -> dict[str, Any]:
    info = page["imageinfo"][0]
    ext = info.get("extmetadata", {})

    def field(name: str) -> str:
        raw = ext.get(name, {})
        return clean_text(raw.get("value") if isinstance(raw, dict) else "")

    licence = field("LicenseShortName")
    return {
        "file_title": page["title"],
        "page_id": page["pageid"],
        "category": category_title(category),
        "license": licence,
        "license_url": field("LicenseUrl"),
        "author": field("Artist"),
        "credit": field("Credit"),
        "source_url": info.get("descriptionurl", ""),
        "original_file_url": info.get("url", ""),
        "mime_type": info.get("mime", ""),
        "width": info.get("width"),
        "height": info.get("height"),
        "file_size_bytes": info.get("size"),
        "copyrighted": field("Copyrighted"),
        "usage_terms": field("UsageTerms"),
    }


def download(url: str, destination: Path, retries: int = 3) -> int:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=120) as response:
                if response.status != 200:
                    raise RuntimeError(f"image download returned HTTP {response.status}")
                data = response.read()
            destination.write_bytes(data)
            return len(data)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            if attempt + 1 == retries:
                raise RuntimeError(f"failed to download {url}: {exc}") from exc
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def collect_category(category: str, limit: int, output_root: Path, dry_run: bool) -> dict[str, Any]:
    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    scanned = reusable_seen = nonfree_skipped = 0
    for page in iter_category_files(category):
        scanned += 1
        metadata = metadata_from_page(page, category)
        if not is_reusable(metadata["license"], metadata["copyrighted"]):
            nonfree_skipped += 1
            continue
        reusable_seen += 1
        selected.append((page, metadata))
        if len(selected) >= limit:
            break

    destination_dir = output_root / class_directory_name(category)
    downloaded = existing = failed = 0
    if not dry_run:
        destination_dir.mkdir(parents=True, exist_ok=True)
        for page, metadata in selected:
            info = page["imageinfo"][0]
            mime = metadata["mime_type"]
            ext = Path(page["title"].split(":", 1)[-1]).suffix
            if not ext:
                ext = mimetypes.guess_extension(mime) or ".bin"
            stem = safe_stem(page["title"], page["pageid"])
            image_path = destination_dir / f"{stem}{ext.lower()}"
            sidecar_path = destination_dir / f"{stem}.json"
            if image_path.exists() and sidecar_path.exists():
                existing += 1
                continue
            try:
                metadata["downloaded_size_bytes"] = download(info["url"], image_path)
                sidecar_path.write_text(
                    json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                downloaded += 1
            except Exception as exc:  # continue so one bad Commons file does not abort the category
                failed += 1
                if image_path.exists() and not sidecar_path.exists():
                    image_path.unlink()
                print(f"ERROR {page['title']}: {exc}", file=sys.stderr)

    summary = {
        "category": category_title(category),
        "output_directory": str(destination_dir),
        "limit": limit,
        "dry_run": dry_run,
        "files_scanned_until_limit": scanned,
        "reusable_selected": len(selected),
        "nonfree_skipped": nonfree_skipped,
        "downloaded": downloaded,
        "already_present": existing,
        "failed": failed,
        "selected": [metadata for _, metadata in selected] if dry_run else [],
    }
    return summary


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Download freely reusable Vietnamese-food images from Wikimedia Commons."
    )
    parser.add_argument(
        "categories",
        nargs="*",
        default=DEFAULT_CATEGORIES,
        help="Commons category names, with or without the 'Category:' prefix",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=200,
        help="maximum reusable images per category (default: 200)",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=project_root / "data" / "raw" / "images",
        help="output root (default: data/raw/images under the project root)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="query and report candidates without creating directories or downloading files",
    )
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")
    return args


def main() -> int:
    args = parse_args()
    all_summaries = []
    for category in args.categories:
        try:
            summary = collect_category(category, args.limit, args.output_root, args.dry_run)
            all_summaries.append(summary)
            print(json.dumps(summary, ensure_ascii=False))
        except Exception as exc:
            print(f"ERROR {category_title(category)}: {exc}", file=sys.stderr)
            return 1
    totals = {
        "categories": len(all_summaries),
        "downloaded": sum(item["downloaded"] for item in all_summaries),
        "reusable_selected": sum(item["reusable_selected"] for item in all_summaries),
        "failed": sum(item["failed"] for item in all_summaries),
    }
    print(json.dumps({"totals": totals}, ensure_ascii=False))
    return 0 if totals["failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
