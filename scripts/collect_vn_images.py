#!/usr/bin/env python3
"""Collect freely reusable Vietnamese-food images from Wikimedia Commons.

Uses only Python's standard library and the public MediaWiki API.  The default
output is data/raw/images/<class>/ relative to the project root.  Every image
has a same-stem .json sidecar containing its Commons provenance and licence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import http.client
import json
import mimetypes
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
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
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp"}
NEGATIVE_TERMS = {
    # Vehicles and registration plates.
    "bus", "citybus", "coach", "vehicle", "automobile", "motorcar", "motorcycle",
    "license plate", "licence plate", "registration plate", "number plate", "biển số", "xe buýt",
    "xe hơi", "ô tô", "ôtô", "xe máy",
    # Shops/signs rather than a photograph of the dish.
    "signboard", "storefront", "shop sign", "restaurant sign", "menu board", "billboard",
    "biển hiệu", "cửa hàng", "mặt tiền", "quán",
    # Non-dish uses of near-homographs/equipment that survive accent folding.
    "xới đất", "máng xối", "cooker",
    # Flowers, fruit and the particularly ambiguous Vietnamese phrase mâm xôi.
    "flower", "flowers", "floral", "blossom", "fruit", "fruits", "raspberry", "raspberries",
    "framboise", "frambuesa", "frambuesas", "mâm xôi", "cúc", "hoa", "trái cây", "quả",
    # Non-food-documentary subjects.
    "logo", "diagram", "chart", "graph", "map", "poster", "advertisement", "drawing",
    "illustration", "painting", "sketch", "icon", "postage stamp", "label", "packaging",
    "package", "packet", "wrapper", "portrait", "selfie", "people", "person", "banknote",
    "coin", "currency", "money", "book", "biểu đồ", "bản đồ", "tranh vẽ", "minh họa",
    "áp phích", "bao bì", "nhãn hiệu", "tem bưu chính", "chân dung", "tiền", "sách",
}
_LAST_REQUEST_AT = 0.0
REQUEST_INTERVAL_SECONDS = 1.05
_CONNECTIONS: dict[str, http.client.HTTPSConnection] = {}


def _pace() -> None:
    global _LAST_REQUEST_AT
    wait = REQUEST_INTERVAL_SECONDS - (time.monotonic() - _LAST_REQUEST_AT)
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST_AT = time.monotonic()


def _paced_open(request: Request, timeout: int):
    """Open at no more than roughly one Wikimedia request per second."""
    global _LAST_REQUEST_AT
    wait = REQUEST_INTERVAL_SECONDS - (time.monotonic() - _LAST_REQUEST_AT)
    if wait > 0:
        time.sleep(wait)
    response = urlopen(request, timeout=timeout)
    _LAST_REQUEST_AT = time.monotonic()
    return response


def api_get(params: dict[str, Any], retries: int = 3) -> dict[str, Any]:
    """GET and decode one MediaWiki API response with bounded retries."""
    query = {"format": "json", "formatversion": "2", **params}
    url = f"{API_URL}?{urlencode(query)}"
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(retries):
        try:
            with _paced_open(request, timeout=60) as response:
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
                "iiurlwidth": "512",
                **continuation,
            }
        )
        for page in payload.get("query", {}).get("pages", []):
            if not page.get("missing") and page.get("imageinfo"):
                yield page
        if "continue" not in payload:
            break
        continuation = payload["continue"]


def iter_search_files(search_term: str, scan_limit: int = 500) -> Iterator[dict[str, Any]]:
    """Yield full-text Commons File results, including category membership."""
    continuation: dict[str, Any] = {}
    yielded = 0
    while yielded < scan_limit:
        payload = api_get(
            {
                "action": "query",
                "generator": "search",
                "gsrsearch": search_term,
                "gsrnamespace": 6,
                "gsrlimit": "max",
                "prop": "imageinfo|categories",
                "iiprop": "url|mime|size|extmetadata",
                "cllimit": "max",
                "iiurlwidth": "512",
                **continuation,
            }
        )
        for page in payload.get("query", {}).get("pages", []):
            if not page.get("missing") and page.get("imageinfo"):
                yield page
                yielded += 1
                if yielded >= scan_limit:
                    return
        if "continue" not in payload:
            break
        continuation = payload["continue"]


def parse_search_spec(spec: str) -> tuple[str, list[str]]:
    if "=" not in spec:
        raise ValueError("search spec must be OUR_CLASS=term or OUR_CLASS=term1|term2")
    class_name, raw_terms = spec.split("=", 1)
    class_name = class_name.strip()
    terms = [term.strip() for term in raw_terms.split("|") if term.strip()]
    if not re.fullmatch(r"[a-z0-9_]+", class_name) or not terms:
        raise ValueError(f"invalid search spec: {spec}")
    return class_name, terms


def _fold(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )


def _words(value: str) -> list[str]:
    """Return accent-free alphanumeric words for boundary-safe matching."""
    return re.findall(r"[a-z0-9]+", _fold(value))


def _contains_phrase(value: str, phrase: str) -> bool:
    haystack = _words(value)
    needle = _words(phrase)
    if not needle:
        return False
    width = len(needle)
    return any(haystack[index:index + width] == needle for index in range(len(haystack) - width + 1))


def acceptance_reason(metadata: dict[str, Any], terms: list[str] | str) -> str | None:
    if isinstance(terms, str):
        terms = [terms]
    title = str(metadata.get("original_filename") or metadata.get("file_title", ""))
    if metadata.get("category") and not metadata.get("search_term"):
        return "source_category"
    categories = [str(value) for value in metadata.get("categories", [])]
    if metadata.get("category"):
        categories.append(str(metadata["category"]))
    if any(_contains_phrase(title, term) for term in terms):
        return "filename_keyword"
    if any(_contains_phrase(category, term) for category in categories for term in terms):
        return "commons_category_keyword"
    return None


def candidate_rejection_reason(
    metadata: dict[str, Any], terms: list[str] | str, class_name: str = "",
) -> str | None:
    if not is_reusable(str(metadata.get("license", "")), str(metadata.get("copyrighted", ""))):
        return "nonfree"
    mime_type = str(metadata.get("mime_type", ""))
    if not mime_type.startswith("image/"):
        return "non_image"
    if mime_type == "image/svg+xml":
        return "quality_filter"
    width, height = int(metadata.get("width") or 0), int(metadata.get("height") or 0)
    if width < 400 or height < 300:
        return "too_small"
    subject_text = " ".join([
        str(metadata.get("original_filename") or metadata.get("file_title", "")),
        str(metadata.get("category", "")),
        *[str(value) for value in metadata.get("categories", [])],
    ])
    if any(_contains_phrase(subject_text, term) for term in NEGATIVE_TERMS):
        return "excluded_subject"
    # A bare XOI followed by digits is a common vehicle registration, not the dish.
    if class_name == "xoi" and re.search(r"\bxoi\s*[- ]?\d+\b", _fold(subject_text)):
        return "excluded_subject"
    if acceptance_reason(metadata, terms) is None:
        return "term_mismatch"
    return None


def metadata_from_page(page: dict[str, Any], category: str) -> dict[str, Any]:
    info = page["imageinfo"][0]
    ext = info.get("extmetadata", {})

    def field(name: str) -> str:
        raw = ext.get(name, {})
        return clean_text(raw.get("value") if isinstance(raw, dict) else "")

    licence = field("LicenseShortName")
    return {
        "file_title": page["title"],
        "original_filename": page["title"].split(":", 1)[-1],
        "page_id": page["pageid"],
        "category": category_title(category) if category.lower().startswith("category:") else "",
        "categories": [item.get("title", "") for item in page.get("categories", []) if item.get("title")],
        "search_term": "" if category.lower().startswith("category:") else category,
        "license": licence,
        "license_url": field("LicenseUrl"),
        "author": field("Artist"),
        "credit": field("Credit"),
        "description": field("ImageDescription") or field("ObjectName"),
        "source_url": info.get("descriptionurl", ""),
        "commons_url": info.get("descriptionurl", ""),
        "original_file_url": info.get("url", ""),
        "download_url": info.get("thumburl") or info.get("url", ""),
        "mime_type": info.get("mime", ""),
        "width": info.get("width"),
        "height": info.get("height"),
        "file_size_bytes": info.get("size"),
        "copyrighted": field("Copyrighted"),
        "usage_terms": field("UsageTerms"),
    }


def download(url: str, destination: Path, retries: int = 1) -> int:
    """Download through a pooled HTTPS connection to avoid repeated TLS setup."""
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError(f"unsupported download URL: {url}")
    request_target = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    for attempt in range(retries):
        connection = _CONNECTIONS.get(parsed.hostname)
        if connection is None:
            connection = http.client.HTTPSConnection(parsed.hostname, timeout=10)
            _CONNECTIONS[parsed.hostname] = connection
        try:
            _pace()
            connection.request("GET", request_target, headers={"User-Agent": USER_AGENT})
            response = connection.getresponse()
            data = response.read()
            if response.status != 200:
                raise RuntimeError(f"image download returned HTTP {response.status}")
            destination.write_bytes(data)
            return len(data)
        except (OSError, http.client.HTTPException, RuntimeError) as exc:
            connection.close()
            _CONNECTIONS.pop(parsed.hostname, None)
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _existing_state(root: Path) -> tuple[set[int], set[str]]:
    page_ids: set[int] = set()
    hashes: set[str] = set()
    for path in root.glob("*/*") if root.exists() else []:
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            match = re.search(r"(?:commons_)?(\d+)", path.stem)
            if match:
                page_ids.add(int(match.group(1)))
            try:
                hashes.add(_sha256(path))
            except OSError:
                pass
    return page_ids, hashes


def fetch_categories(page_ids: list[int]) -> dict[int, list[str]]:
    """Fetch Commons category names in API-sized batches for old sidecars."""
    result: dict[int, list[str]] = {}
    for start in range(0, len(page_ids), 50):
        batch = page_ids[start:start + 50]
        payload = api_get({
            "action": "query", "pageids": "|".join(str(value) for value in batch),
            "prop": "categories", "cllimit": "max",
        })
        for page in payload.get("query", {}).get("pages", []):
            if page.get("pageid") is not None:
                result[int(page["pageid"])] = [
                    item.get("title", "") for item in page.get("categories", []) if item.get("title")
                ]
    return result


def audit_existing_class(class_name: str, terms: list[str], output_root: Path) -> dict[str, Any]:
    """Move existing files that fail the strict relevance gate to _rejected."""
    class_dir = output_root / class_name
    images = sorted(path for path in class_dir.glob("*") if path.suffix.lower() in IMAGE_SUFFIXES)
    loaded: list[tuple[Path, Path, dict[str, Any]]] = []
    ids_needing_categories: list[int] = []
    for image in images:
        sidecar = image.with_suffix(".json")
        metadata: dict[str, Any] = {}
        if sidecar.exists():
            try:
                metadata = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                metadata = {}
        loaded.append((image, sidecar, metadata))
        page_id = metadata.get("page_id")
        if page_id and not metadata.get("categories") and not metadata.get("category"):
            ids_needing_categories.append(int(page_id))
    category_map = fetch_categories(ids_needing_categories) if ids_needing_categories else {}
    rejected_dir = output_root / "_rejected" / class_name
    rejection_rows: list[dict[str, Any]] = []
    clean = 0
    for image, sidecar, metadata in loaded:
        page_id = metadata.get("page_id")
        numeric_page_id = int(str(page_id)) if str(page_id).isdigit() else None
        if numeric_page_id in category_map:
            metadata["categories"] = category_map[numeric_page_id]
        reason = "missing_metadata" if not metadata else candidate_rejection_reason(metadata, terms, class_name)
        if reason is None:
            metadata["acceptance_reason"] = acceptance_reason(metadata, terms)
            sidecar.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            clean += 1
            continue
        rejected_dir.mkdir(parents=True, exist_ok=True)
        destination = rejected_dir / image.name
        destination.unlink(missing_ok=True)
        image.replace(destination)
        rejected_sidecar = rejected_dir / sidecar.name
        rejected_sidecar.unlink(missing_ok=True)
        if sidecar.exists():
            sidecar.replace(rejected_sidecar)
        rejection_rows.append({
            "our_class": class_name,
            "local_file": f"data/raw/images/{class_name}/{image.name}",
            "original_filename": metadata.get("original_filename") or metadata.get("file_title", image.name),
            "page_id": metadata.get("page_id", ""),
            "reason": reason,
        })
    return {
        "our_class": class_name, "initial": len(images), "clean": clean,
        "rejected": len(rejection_rows), "rejection_rows": rejection_rows,
        "rejection_reasons": dict(sorted(Counter(row["reason"] for row in rejection_rows).items())),
    }


def write_rejection_log(rows: list[dict[str, Any]], reports_root: Path) -> Path:
    path = reports_root / "commons_rejections.csv"
    reports_root.mkdir(parents=True, exist_ok=True)
    fields = ["our_class", "local_file", "original_filename", "page_id", "reason"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _copy_staging_provenance(project_root: Path, output_root: Path) -> None:
    staging = project_root / "data" / "processed" / ".commons_staging"
    by_id = {path.stem.split("_", 1)[0]: path for path in staging.glob("*/*.json")} if staging.exists() else {}
    for image in output_root.glob("*/commons_*.*") if output_root.exists() else []:
        if image.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        page_id = image.stem.split("_", 1)[1]
        sidecar = image.with_suffix(".json")
        if not sidecar.exists() and page_id in by_id:
            sidecar.write_text(by_id[page_id].read_text(encoding="utf-8"), encoding="utf-8")


def collect_search_class(
    class_name: str, terms: list[str], limit: int, output_root: Path, scan_limit: int,
    dry_run: bool, page_ids: set[int], hashes: set[str],
) -> dict[str, Any]:
    destination = output_root / class_name
    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)
    initial = sum(1 for path in destination.glob("*") if path.suffix.lower() in IMAGE_SUFFIXES) if destination.exists() else 0
    seen: set[int] = set()
    eligible: list[tuple[dict[str, Any], dict[str, Any]]] = []
    rejected: Counter[str] = Counter()
    scanned = 0
    for term in terms:
        for page in iter_search_files(term, scan_limit):
            scanned += 1
            page_id = int(page["pageid"])
            if page_id in seen:
                rejected["duplicate_page_id"] += 1
                continue
            seen.add(page_id)
            metadata = metadata_from_page(page, term)
            reason = candidate_rejection_reason(metadata, terms, class_name)
            if reason:
                rejected[reason] += 1
            else:
                metadata["acceptance_reason"] = acceptance_reason(metadata, terms)
                eligible.append((page, metadata))
    downloaded = present = duplicate_content = failed = 0
    for page, metadata in eligible:
        if initial + downloaded >= limit:
            break
        page_id = int(page["pageid"])
        if page_id in page_ids:
            present += 1
            continue
        extension = Path(metadata["original_filename"]).suffix.lower()
        if extension not in IMAGE_SUFFIXES:
            extension = mimetypes.guess_extension(metadata["mime_type"]) or ".jpg"
        image_path = destination / f"commons_{page_id}{extension}"
        sidecar_path = destination / f"commons_{page_id}.json"
        if dry_run:
            continue
        try:
            metadata["our_class"] = class_name
            metadata["downloaded_size_bytes"] = download(metadata["download_url"], image_path)
            digest = _sha256(image_path)
            if digest in hashes:
                duplicate_content += 1
                image_path.unlink(missing_ok=True)
                continue
            metadata["sha256"] = digest
            sidecar_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            hashes.add(digest)
            page_ids.add(page_id)
            downloaded += 1
        except Exception as exc:
            failed += 1
            image_path.unlink(missing_ok=True)
            sidecar_path.unlink(missing_ok=True)
            print(f"ERROR {page['title']}: {exc}", file=sys.stderr)
    return {
        "our_class": class_name, "search_terms": terms, "limit": limit,
        "scan_limit_per_term": scan_limit, "scanned": scanned, "eligible": len(eligible),
        "initial_images": initial, "downloaded": downloaded, "final_images": initial + downloaded,
        "already_present_page_id": present, "duplicate_content": duplicate_content,
        "failed": failed, "rejected": dict(sorted(rejected.items())),
    }


def write_contact_sheet(class_dir: Path, destination: Path, max_images: int = 100) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageOps
    except ImportError:
        return False
    paths = [path for path in sorted(class_dir.glob("*")) if path.suffix.lower() in IMAGE_SUFFIXES][:max_images]
    if not paths:
        return False
    cell_w, cell_h, columns = 180, 150, 5
    sheet = Image.new("RGB", (columns * cell_w, ((len(paths) + columns - 1) // columns) * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        try:
            with Image.open(path) as source:
                thumb = ImageOps.contain(source.convert("RGB"), (cell_w - 8, cell_h - 28))
            x, y = (index % columns) * cell_w, (index // columns) * cell_h
            sheet.paste(thumb, (x + (cell_w - thumb.width) // 2, y + 2))
            draw.text((x + 4, y + cell_h - 22), path.stem[:25], fill="black")
        except OSError:
            pass
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, "JPEG", quality=85)
    return True


def write_provenance(output_root: Path, reports_root: Path, class_names: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for class_name in class_names:
        class_dir = output_root / class_name
        for image in sorted(path for path in class_dir.glob("*") if path.suffix.lower() in IMAGE_SUFFIXES):
            sidecar = image.with_suffix(".json")
            metadata: dict[str, Any] = {}
            if sidecar.exists():
                try:
                    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    pass
            rows.append({
                "our_class": class_name, "local_file": f"data/raw/images/{class_name}/{image.name}",
                "original_filename": metadata.get("original_filename") or metadata.get("file_title", ""),
                "page_id": metadata.get("page_id", ""), "author": metadata.get("author", ""),
                "license": metadata.get("license", ""), "license_url": metadata.get("license_url", ""),
                "commons_url": metadata.get("commons_url") or metadata.get("source_url", ""),
                "search_term": metadata.get("search_term", "") or metadata.get("category", ""),
                "acceptance_reason": metadata.get("acceptance_reason", ""),
                "sha256": metadata.get("sha256") or _sha256(image),
            })
    reports_root.mkdir(parents=True, exist_ok=True)
    fields = ["our_class", "local_file", "original_filename", "page_id", "author", "license", "license_url", "commons_url", "search_term", "acceptance_reason", "sha256"]
    with (reports_root / "commons_provenance.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (reports_root / "commons_provenance.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rows


def write_collection_report(summaries: list[dict[str, Any]], rows: list[dict[str, Any]], reports_root: Path, contacts: dict[str, Path]) -> Path:
    path = reports_root / "commons_collection_report.md"
    licenses = sorted({str(row["license"]) for row in rows if row["license"]})
    missing = sum(1 for row in rows if not row["license"] or not row["commons_url"])
    lines = [
        "# Báo cáo thu thập ảnh Wikimedia Commons", "",
        "> Cổng tự động chỉ giữ ảnh có cụm từ món (khớp từ trọn vẹn, bỏ dấu) trong tên file Commons hoặc trong tên danh mục Commons; các chủ đề ngoại lệ rõ ràng bị loại. Contact sheet vẫn cần được duyệt bằng mắt trước khi huấn luyện.", "",
        "| Lớp | Ảnh sạch còn lại | Ảnh bị loại | Lý do loại phổ biến nhất | Contact sheet |",
        "|---|---:|---:|---|---|",
    ]
    for summary in summaries:
        contact = contacts.get(summary["our_class"])
        link = f"[{contact.name}](contact_sheets/{contact.name})" if contact else "Không tạo được"
        reasons = Counter(summary.get("audit_rejection_reasons", {}))
        common = reasons.most_common(1)[0][0] if reasons else "—"
        lines.append(
            f"| `{summary['our_class']}` | {summary['final_images']} | {summary.get('audit_rejected', 0)} | "
            f"{common} | {link} |"
        )
    total_clean = sum(item["final_images"] for item in summaries)
    total_rejected = sum(item.get("audit_rejected", 0) for item in summaries)
    lines += [
        "", f"- Tổng ảnh sạch trong 21 lớp món Việt: **{total_clean}**.",
        f"- Tổng ảnh bị loại và chuyển sang `_rejected`: **{total_rejected}**.",
        f"- Giấy phép gặp: {', '.join(licenses) or 'không có'}.",
        f"- Ảnh sạch thiếu metadata giấy phép hoặc URL: **{missing}**.",
        "- Truy nguyên: [`commons_provenance.csv`](commons_provenance.csv), [`commons_provenance.json`](commons_provenance.json).",
        "- Nhật ký loại: [`commons_rejections.csv`](commons_rejections.csv).",
        "", "## Lớp dưới 35 ảnh sạch (đề xuất loại khỏi tập huấn luyện)", "",
    ]
    under = [item for item in summaries if item["final_images"] < 35]
    lines += [f"- `{item['our_class']}`: **{item['final_images']}** ảnh sạch." for item in under] or ["- Không có."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Download freely reusable Vietnamese-food images from Wikimedia Commons.")
    parser.add_argument("items", nargs="*", help="categories, or OUR_CLASS=term1|term2 in search mode")
    parser.add_argument("--mode", choices=("category", "search"), default="category")
    parser.add_argument("--search", action="store_true", help="alias for --mode search")
    parser.add_argument("-n", "--limit", type=int, default=200)
    parser.add_argument("--scan-limit", type=int, default=500)
    parser.add_argument("--output-root", type=Path, default=project_root / "data" / "raw" / "images")
    parser.add_argument("--reports-root", type=Path, default=project_root / "data" / "reports")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.search:
        args.mode = "search"
    if args.limit < 1 or args.scan_limit < 1:
        parser.error("--limit and --scan-limit must be at least 1")
    if not args.items and args.mode == "category":
        args.items = DEFAULT_CATEGORIES
    if not args.items and args.mode == "search":
        parser.error("search mode requires OUR_CLASS=term")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.mode == "category":
        summaries = [collect_category(item, args.limit, args.output_root, args.dry_run) for item in args.items]
        for summary in summaries:
            print(json.dumps(summary, ensure_ascii=False))
        return 0 if not any(item["failed"] for item in summaries) else 2
    project_root = Path(__file__).resolve().parents[1]
    _copy_staging_provenance(project_root, args.output_root)
    specs = [parse_search_spec(item) for item in args.items]
    audits = [audit_existing_class(class_name, terms, args.output_root) for class_name, terms in specs]
    audit_by_class = {item["our_class"]: item for item in audits}
    rejection_rows = [row for item in audits for row in item["rejection_rows"]]
    if not args.dry_run:
        write_rejection_log(rejection_rows, args.reports_root)
    page_ids, hashes = _existing_state(args.output_root)
    summaries = []
    for class_name, terms in specs:
        summary = collect_search_class(class_name, terms, args.limit, args.output_root, args.scan_limit, args.dry_run, page_ids, hashes)
        audit = audit_by_class[class_name]
        summary["audit_rejected"] = audit["rejected"]
        summary["audit_rejection_reasons"] = audit["rejection_reasons"]
        summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    if not args.dry_run:
        contacts: dict[str, Path] = {}
        for class_name, _ in specs:
            destination = args.reports_root / "contact_sheets" / f"{class_name}.jpg"
            if write_contact_sheet(args.output_root / class_name, destination):
                contacts[class_name] = destination
        rows = write_provenance(args.output_root, args.reports_root, [name for name, _ in specs])
        report = write_collection_report(summaries, rows, args.reports_root, contacts)
        print(json.dumps({"report": str(report), "total_downloaded": sum(item["downloaded"] for item in summaries)}, ensure_ascii=False))
    return 0 if not any(item["failed"] for item in summaries) else 2


if __name__ == "__main__":
    raise SystemExit(main())
