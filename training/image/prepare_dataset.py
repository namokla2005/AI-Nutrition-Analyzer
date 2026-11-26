#!/usr/bin/env python3
"""Prepare a bounded, provenance-aware image dataset for food recognition.

Food-101 is streamed from Hugging Face and filtered before image decoding.
Vietnamese dishes are collected with scripts/collect_vn_images.py so each
Commons file keeps its per-file licence metadata.  Output images are JPEGs
whose longest side is at most 512 px; the trainer owns the 224x224 transform.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import mimetypes
import random
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.request import Request, urlopen

from PIL import Image, ImageOps, UnidentifiedImageError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLASS_MAP_PATH = Path(__file__).with_name("class_map.json")
RAW_IMAGE_ROOT = PROJECT_ROOT / "data" / "raw" / "images"
PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
MANIFEST_PATH = PROCESSED_ROOT / "image_dataset_manifest.csv"
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "image_dataset_report.md"
RUN_METADATA_PATH = PROCESSED_ROOT / "image_dataset_run.json"
COMMONS_STAGING_ROOT = PROCESSED_ROOT / ".commons_staging"
HF_CACHE_ROOT = PROCESSED_ROOT / ".hf_cache"
DEFAULT_CAP = 300
DEFAULT_SEED = 20261119
DEFAULT_MINIMUM_TRAINABLE = 100
MAX_SIDE = 512
JPEG_QUALITY = 85
TARGET_CLASSES = {
    "pho_bo",
    "bun_bo_hue",
    "banh_mi",
    "com_tam",
    "goi_cuon",
    "banh_xeo",
    "bun_cha",
    "com_chien",
    "pizza",
    "hamburger",
    "sushi",
    "salad",
    "pasta",
    "steak",
    "fried_chicken",
    "xoi",
    "pho_ga",
    "banh_cuon",
    "hu_tieu",
    "mi_quang",
    "cha_ca",
    "nem_ran",
    "canh_chua",
    "banh_chung",
    "banh_khot",
    "bun_rieu",
    "banh_beo",
    "bun_dau_mam_tom",
    "bun_thit_nuong",
}
MANIFEST_COLUMNS = [
    "our_class",
    "source_class",
    "source",
    "split",
    "relative_path",
    "width",
    "height",
    "bytes",
    "licence/source note",
]
FOOD101_TRAIN_SHARDS = [
    ("train-00000-of-00008.parquet", 489_582_959),
    ("train-00001-of-00008.parquet", 464_225_341),
    ("train-00002-of-00008.parquet", 472_211_726),
    ("train-00003-of-00008.parquet", 463_644_865),
    ("train-00004-of-00008.parquet", 475_091_267),
    ("train-00005-of-00008.parquet", 469_875_468),
    ("train-00006-of-00008.parquet", 478_240_948),
    ("train-00007-of-00008.parquet", 485_648_421),
]
FOOD101_NOTE = (
    "Food-101/ETHZ via Hugging Face; images originate from Foodspotting; "
    "scientific fair use only; not an open-image licence"
)


def load_class_map(path: Path = CLASS_MAP_PATH) -> list[dict[str, Any]]:
    mapping = json.loads(path.read_text(encoding="utf-8"))
    names = [item["our_class"] for item in mapping]
    if len(names) != len(set(names)) or set(names) != TARGET_CLASSES:
        raise ValueError(f"class_map.json phải chứa đúng {len(TARGET_CLASSES)} lớp đích, không trùng tên")
    valid_coverage = {"exact", "approximate", "not_covered"}
    for item in mapping:
        if item["coverage_type"] not in valid_coverage:
            raise ValueError(f"coverage_type không hợp lệ: {item}")
        if item["selected_source"] not in {"food101", "commons"}:
            raise ValueError(f"selected_source không hợp lệ: {item}")
    return mapping


def _rgb_image(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def save_pil_as_jpeg(
    image: Image.Image,
    destination: Path,
    max_side: int = MAX_SIDE,
    quality: int = JPEG_QUALITY,
) -> tuple[int, int, int]:
    image = _rgb_image(image)
    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    image.save(temporary, format="JPEG", quality=quality, optimize=True)
    temporary.replace(destination)
    width, height = image.size
    return width, height, destination.stat().st_size


def resize_to_jpeg(
    source: Path,
    destination: Path,
    max_side: int = MAX_SIDE,
    quality: int = JPEG_QUALITY,
) -> tuple[int, int, int]:
    with Image.open(source) as image:
        return save_pil_as_jpeg(image, destination, max_side=max_side, quality=quality)


def _file_identity(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _split_sizes(count: int) -> tuple[int, int, int]:
    if count <= 0:
        return 0, 0, 0
    raw = [count * 0.70, count * 0.15, count * 0.15]
    sizes = [math.floor(value) for value in raw]
    for index in sorted(range(3), key=lambda idx: raw[idx] - sizes[idx], reverse=True)[: count - sum(sizes)]:
        sizes[index] += 1
    if count >= 3:
        for index in (1, 2):
            if sizes[index] == 0:
                donor = max(range(3), key=lambda idx: sizes[idx])
                sizes[donor] -= 1
                sizes[index] += 1
    return sizes[0], sizes[1], sizes[2]


def assign_splits(records: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    identities = [record["identity"] for record in records]
    if len(identities) != len(set(identities)):
        raise ValueError("Trùng định danh ảnh: một ảnh không được xuất hiện nhiều lần")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["our_class"]].append(dict(record))
    result: list[dict[str, Any]] = []
    for class_name in sorted(grouped):
        items = sorted(grouped[class_name], key=lambda item: (item["identity"], item["relative_path"]))
        class_seed = seed + int(hashlib.sha256(class_name.encode()).hexdigest()[:8], 16)
        random.Random(class_seed).shuffle(items)
        train_size, val_size, _ = _split_sizes(len(items))
        for index, item in enumerate(items):
            item["split"] = "train" if index < train_size else "val" if index < train_size + val_size else "test"
            result.append(item)
    return sorted(result, key=lambda item: (item["our_class"], item["split"], item["relative_path"]))


def write_manifest(records: Iterable[dict[str, Any]], path: Path = MANIFEST_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)
    temporary.replace(path)


def _food101_targets(mapping: list[dict[str, Any]]) -> dict[str, str]:
    targets: dict[str, str] = {}
    for item in mapping:
        if item["selected_source"] != "food101":
            continue
        for source_class in item["food101_classes"]:
            if source_class in targets:
                raise ValueError(f"Lớp Food-101 được ánh xạ hai lần: {source_class}")
            targets[source_class] = item["our_class"]
    return targets


def _payload_bytes(payload: Any) -> bytes:
    if isinstance(payload, dict):
        if payload.get("bytes") is not None:
            return payload["bytes"]
        if payload.get("path"):
            path = str(payload["path"])
            if path.startswith(("http://", "https://")):
                with urlopen(Request(path, headers={"User-Agent": "AI-Nutrition-Analyzer/1.0"}), timeout=120) as response:
                    return response.read()
            return Path(path).read_bytes()
    raise ValueError("Không đọc được payload ảnh Food-101")


def _record_food101_image(
    raw: bytes,
    row_index: int,
    source_class: str,
    our_class: str,
    seen_identities: set[str],
) -> dict[str, Any] | None:
    destination = RAW_IMAGE_ROOT / our_class / f"food101_train_{row_index:06d}_{source_class}.jpg"
    try:
        with Image.open(io.BytesIO(raw)) as image:
            width, height, size = save_pil_as_jpeg(image, destination)
    except (OSError, UnidentifiedImageError, ValueError):
        destination.unlink(missing_ok=True)
        return None
    identity = _file_identity(destination)
    if identity in seen_identities:
        destination.unlink(missing_ok=True)
        return None
    seen_identities.add(identity)
    return {
        "our_class": our_class,
        "source_class": source_class,
        "source": "food101",
        "relative_path": _relative(destination),
        "width": width,
        "height": height,
        "bytes": size,
        "licence/source note": FOOD101_NOTE,
        "identity": identity,
        "source_payload_bytes": len(raw),
    }


def collect_food101_streaming(
    mapping: list[dict[str, Any]], cap: int, seen_identities: set[str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        from datasets import Image as HFImage
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("Cần cài packages 'datasets' và 'pyarrow' vào venv") from exc

    HF_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    targets = _food101_targets(mapping)
    counts = Counter({class_name: 0 for class_name in set(targets.values())})
    records: list[dict[str, Any]] = []
    rows_scanned = 0
    dataset = load_dataset(
        "ethz/food101",
        split="train",
        streaming=True,
        cache_dir=str(HF_CACHE_ROOT),
    ).cast_column("image", HFImage(decode=False))
    label_names = dataset.features["label"].names
    for row_index, row in enumerate(dataset):
        rows_scanned += 1
        numeric_label = row["label"]
        source_class = label_names[numeric_label] if isinstance(numeric_label, int) else str(numeric_label)
        our_class = targets.get(source_class)
        if our_class is None or counts[our_class] >= cap:
            continue
        raw = _payload_bytes(row["image"])
        record = _record_food101_image(raw, row_index, source_class, our_class, seen_identities)
        if record is not None:
            records.append(record)
            counts[our_class] += 1
        if all(counts[class_name] >= cap for class_name in counts):
            break
    stats = {
        "method": "huggingface_datasets_streaming",
        "rows_scanned": rows_scanned,
        "selected_source_payload_bytes": sum(item["source_payload_bytes"] for item in records),
        "downloaded_shards": [],
        "counts": dict(sorted(counts.items())),
    }
    return records, stats


def _download_file(url: str, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = Request(url, headers={"User-Agent": "AI-Nutrition-Analyzer/1.0 (academic use)"})
    with urlopen(request, timeout=180) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)
    temporary.replace(destination)
    return destination.stat().st_size


def collect_food101_parquet_fallback(
    mapping: list[dict[str, Any]], cap: int, seen_identities: set[str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    import pyarrow.parquet as pq

    targets = _food101_targets(mapping)
    counts = Counter({class_name: 0 for class_name in set(targets.values())})
    records: list[dict[str, Any]] = []
    downloaded_shards: list[dict[str, Any]] = []
    shard_root = PROCESSED_ROOT / ".food101_shards"
    global_row = 0
    from datasets import load_dataset

    label_feature = load_dataset(
        "ethz/food101", split="train", streaming=True, cache_dir=str(HF_CACHE_ROOT)
    ).features["label"]
    for filename, expected_size in FOOD101_TRAIN_SHARDS:
        path = shard_root / filename
        network_bytes = 0
        if not path.exists() or path.stat().st_size != expected_size:
            path.unlink(missing_ok=True)
            url = f"https://huggingface.co/datasets/ethz/food101/resolve/main/data/{filename}"
            network_bytes = _download_file(url, path)
        downloaded_shards.append(
            {
                "file": filename,
                "stored_bytes": path.stat().st_size,
                "network_bytes_this_run": network_bytes,
            }
        )
        parquet_file = pq.ParquetFile(path)
        for batch in parquet_file.iter_batches(columns=["image", "label"], batch_size=128):
            for row in batch.to_pylist():
                label = row["label"]
                source_class = label if isinstance(label, str) else str(label)
                if isinstance(label, int):
                    source_class = label_feature.names[label]
                our_class = targets.get(source_class)
                if our_class is not None and counts[our_class] < cap:
                    raw = _payload_bytes(row["image"])
                    record = _record_food101_image(
                        raw, global_row, source_class, our_class, seen_identities
                    )
                    if record is not None:
                        records.append(record)
                        counts[our_class] += 1
                global_row += 1
                if all(counts[class_name] >= cap for class_name in counts):
                    break
            if all(counts[class_name] >= cap for class_name in counts):
                break
        if all(counts[class_name] >= cap for class_name in counts):
            break
    return records, {
        "method": "individual_parquet_shards_fallback",
        "rows_scanned": global_row,
        "selected_source_payload_bytes": sum(item["source_payload_bytes"] for item in records),
        "downloaded_shards": downloaded_shards,
        "counts": dict(sorted(counts.items())),
    }


def collect_food101(
    mapping: list[dict[str, Any]], cap: int, seen_identities: set[str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reuse complete local Food-101 classes before attempting network streaming."""
    local_records: list[dict[str, Any]] = []
    local_counts: dict[str, int] = {}
    local_complete = True
    for item in mapping:
        if item["selected_source"] != "food101":
            continue
        candidates = sorted((RAW_IMAGE_ROOT / item["our_class"]).glob("food101_*.jpg"))[:cap]
        local_counts[item["our_class"]] = len(candidates)
        if len(candidates) < cap:
            local_complete = False
            break
        for path in candidates:
            try:
                with Image.open(path) as image:
                    width, height = image.size
                identity = _file_identity(path)
            except (OSError, UnidentifiedImageError):
                local_complete = False
                break
            if identity in seen_identities:
                continue
            seen_identities.add(identity)
            local_records.append({
                "our_class": item["our_class"], "source_class": item["source_class"],
                "source": "food101", "relative_path": _relative(path), "width": width,
                "height": height, "bytes": path.stat().st_size, "licence/source note": FOOD101_NOTE,
                "identity": identity, "source_payload_bytes": path.stat().st_size,
            })
    if local_complete:
        return local_records, {
            "method": "existing_local_food101_images", "rows_scanned": 0,
            "selected_source_payload_bytes": sum(item["source_payload_bytes"] for item in local_records),
            "downloaded_shards": [], "counts": dict(sorted(local_counts.items())),
        }
    seen_identities.difference_update(item["identity"] for item in local_records)
    try:
        return collect_food101_streaming(mapping, cap, seen_identities)
    except Exception as exc:
        print(f"CẢNH BÁO: streaming Food-101 thất bại ({exc}); chuyển sang tải shard riêng.", file=sys.stderr)
        records, stats = collect_food101_parquet_fallback(mapping, cap, seen_identities)
        stats["streaming_error"] = repr(exc)
        return records, stats


def _load_commons_collector() -> Any:
    path = PROJECT_ROOT / "scripts" / "collect_vn_images.py"
    spec = importlib.util.spec_from_file_location("collect_vn_images", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Không thể nạp collector: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source_image_for_sidecar(sidecar: Path) -> Path | None:
    candidates = [
        path
        for path in sidecar.parent.glob(sidecar.stem + ".*")
        if path != sidecar and not path.name.endswith(".part")
    ]
    return sorted(candidates)[0] if candidates else None


def _stage_commons_category(
    collector: Any, category: str, limit: int, throttle_seconds: float = 0.75
) -> dict[str, Any]:
    """Use the existing collector's API/licence helpers with 1600px thumbnails.

    collect_vn_images.py requests thumbnail metadata but its CLI downloads the
    original URL.  This integration keeps all of its licence decisions and
    sidecar fields while choosing the bounded thumbnail URL and pacing image
    requests to avoid Wikimedia HTTP 429 responses.
    """
    destination_dir = COMMONS_STAGING_ROOT / collector.class_directory_name(category)
    destination_dir.mkdir(parents=True, exist_ok=True)
    scanned = reusable_seen = nonfree_skipped = nonimage_skipped = 0
    downloaded = existing = failed = 0
    for page in collector.iter_category_files(category):
        scanned += 1
        metadata = collector.metadata_from_page(page, category)
        if not collector.is_reusable(metadata["license"], metadata["copyrighted"]):
            nonfree_skipped += 1
            continue
        info = page["imageinfo"][0]
        if not str(info.get("mime", "")).startswith("image/"):
            nonimage_skipped += 1
            continue
        reusable_seen += 1
        extension = Path(page["title"].split(":", 1)[-1]).suffix
        if not extension:
            extension = mimetypes.guess_extension(metadata.get("mime_type", "")) or ".bin"
        stem = collector.safe_stem(page["title"], page["pageid"])
        image_path = destination_dir / f"{stem}{extension.lower()}"
        sidecar_path = destination_dir / f"{stem}.json"
        if image_path.exists() and sidecar_path.exists():
            existing += 1
        else:
            try:
                time.sleep(throttle_seconds)
                download_url = info.get("thumburl") or info["url"]
                metadata["downloaded_size_bytes"] = collector.download(download_url, image_path)
                metadata["download_url"] = download_url
                sidecar_path.write_text(
                    json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                downloaded += 1
            except Exception as exc:
                failed += 1
                image_path.unlink(missing_ok=True)
                print(f"ERROR {page['title']}: {exc}", file=sys.stderr)
        if downloaded + existing >= limit:
            break
    return {
        "category": collector.category_title(category),
        "output_directory": str(destination_dir),
        "limit": limit,
        "files_scanned_until_limit": scanned,
        "reusable_images_seen": reusable_seen,
        "nonfree_skipped": nonfree_skipped,
        "nonimage_skipped": nonimage_skipped,
        "downloaded": downloaded,
        "already_present": existing,
        "failed": failed,
    }


def collect_commons(
    mapping: list[dict[str, Any]], cap: int, seen_identities: set[str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Normalize already collected Commons files and preserve sidecar provenance."""
    records: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    failed_processing: list[str] = []
    image_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp"}
    for item in mapping:
        if item["selected_source"] != "commons":
            continue
        class_dir = RAW_IMAGE_ROOT / item["our_class"]
        candidates = sorted(path for path in class_dir.glob("*") if path.suffix.lower() in image_suffixes)
        accepted = 0
        for source_image in candidates:
            if accepted >= cap:
                break
            page_match = re.search(r"(?:commons_)?(\d+)", source_image.stem)
            page_id = page_match.group(1) if page_match else source_image.stem
            sidecar = source_image.with_suffix(".json")
            metadata: dict[str, Any] = {}
            if sidecar.exists():
                try:
                    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    failed_processing.append(f"{sidecar}: metadata lỗi: {exc}")
            destination = class_dir / f"commons_{page_id}.jpg"
            temporary = class_dir / f".prepare_{page_id}.jpg"
            try:
                width, height, size = resize_to_jpeg(source_image, temporary)
                temporary.replace(destination)
                if source_image != destination:
                    source_image.unlink(missing_ok=True)
                if sidecar.exists() and sidecar != destination.with_suffix(".json"):
                    sidecar.replace(destination.with_suffix(".json"))
            except (OSError, UnidentifiedImageError, ValueError) as exc:
                temporary.unlink(missing_ok=True)
                failed_processing.append(f"{source_image}: {exc}")
                continue
            identity = _file_identity(destination)
            if identity in seen_identities:
                failed_processing.append(f"{source_image}: ảnh trùng nội dung")
                continue
            seen_identities.add(identity)
            source_class = item.get("search_term") or item["source_class"]
            note_parts = [
                f"Wikimedia Commons {metadata.get('license', 'không rõ giấy phép')}",
                f"author={metadata.get('author', '')}",
                f"source={metadata.get('commons_url') or metadata.get('source_url', '')}",
                f"license_url={metadata.get('license_url', '')}",
            ]
            records.append({
                "our_class": item["our_class"], "source_class": source_class, "source": "commons",
                "relative_path": _relative(destination), "width": width, "height": height, "bytes": size,
                "licence/source note": "; ".join(note_parts), "identity": identity,
                "source_payload_bytes": int(metadata.get("downloaded_size_bytes") or size),
                "commons_license": metadata.get("license", ""),
            })
            accepted += 1
        summaries.append({"our_class": item["our_class"], "source_class": item.get("search_term") or item["source_class"],
                          "available": len(candidates), "accepted": accepted, "failed": len(candidates[:cap]) - accepted})
    return records, {
        "method": "existing data/raw/images with Commons sidecars",
        "collector_summaries": summaries,
        "selected_source_payload_bytes": sum(item["source_payload_bytes"] for item in records),
        "processing_failures": failed_processing,
        "counts": dict(sorted(Counter(item["our_class"] for item in records).items())),
    }


def _format_bytes(value: int) -> str:
    return f"{value:,} byte ({value / (1024 * 1024):.2f} MiB)".replace(",", ".")


def write_report(
    records: list[dict[str, Any]],
    mapping: list[dict[str, Any]],
    cap: int,
    seed: int,
    minimum_trainable: int,
    source_stats: dict[str, Any],
    path: Path = REPORT_PATH,
) -> None:
    by_class_split = Counter((row["our_class"], row["split"]) for row in records)
    by_class = Counter(row["our_class"] for row in records)
    by_source = Counter(row["source"] for row in records)
    bytes_by_source = Counter()
    for row in records:
        bytes_by_source[row["source"]] += int(row["bytes"])
    map_by_name = {item["our_class"]: item for item in mapping}
    too_few = [name for name in sorted(TARGET_CLASSES) if by_class[name] < minimum_trainable]
    payload_bytes = sum(
        int(stats.get("selected_source_payload_bytes", 0)) for stats in source_stats.values()
    )
    output_bytes = sum(int(row["bytes"]) for row in records)
    split_totals = Counter(row["split"] for row in records)
    lines = [
        "# Báo cáo chuẩn bị bộ ảnh nhận diện món ăn",
        "",
        f"- Thời điểm tạo: `{datetime.now().astimezone().isoformat(timespec='seconds')}`",
        f"- Giới hạn lần chạy: **{cap} ảnh/lớp** (mặc định của script: {DEFAULT_CAP}).",
        f"- Seed chia tập: **{seed}**; tỷ lệ mục tiêu theo từng lớp: **70% train / 15% val / 15% test**.",
        f"- Kích thước ảnh đầu ra: cạnh dài tối đa **{MAX_SIDE}px**, JPEG quality **{JPEG_QUALITY}**; resize 224×224 để trainer thực hiện.",
        f"- Tổng ảnh JPEG thực có trong manifest: **{len(records)}**; tổng dung lượng JPEG trên đĩa: **{_format_bytes(output_bytes)}**.",
        f"- Tổng payload tệp ảnh nguồn đã chọn được tải/đọc: **{_format_bytes(payload_bytes)}**. Với streaming Parquet, đây không phải tổng lưu lượng HTTP vì thư viện không công bố số byte range/chunk đã truyền.",
        "",
        "## Kết quả thực tế theo lớp",
        "",
        "| Lớp dự án | Tên hiển thị | Nguồn chọn | Kiểu phủ Food-101 | Train | Val | Test | Tổng | Byte JPEG |",
        "|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for class_name in sorted(TARGET_CLASSES):
        item = map_by_name[class_name]
        class_bytes = sum(int(row["bytes"]) for row in records if row["our_class"] == class_name)
        lines.append(
            f"| `{class_name}` | {item['display_name_vi']} | {item['selected_source']} | "
            f"{item['coverage_type']} | {by_class_split[class_name, 'train']} | "
            f"{by_class_split[class_name, 'val']} | {by_class_split[class_name, 'test']} | "
            f"{by_class[class_name]} | {class_bytes:,} |"
        )
    lines.extend(
        [
            "",
            "## Quy mô split",
            "",
            f"- Train: **{split_totals['train']}** ảnh.",
            f"- Validation (`val`): **{split_totals['val']}** ảnh.",
            f"- Test: **{split_totals['test']}** ảnh.",
            "- Ảnh được nhận diện bằng SHA-256 của JPEG chuẩn hóa; script từ chối định danh trùng, nên một ảnh không thể nằm ở hai split.",
            "",
            "## Lớp có quá ít ảnh để huấn luyện",
            "",
            f"Ngưỡng vận hành được khai báo cho báo cáo này là **{minimum_trainable} ảnh/lớp** (có thể đổi bằng `--minimum-trainable`).",
            "",
        ]
    )
    if too_few:
        for class_name in too_few:
            lines.append(f"- `{class_name}`: **{by_class[class_name]}** ảnh (< {minimum_trainable}).")
    else:
        lines.append("- Không có lớp nào dưới ngưỡng đã khai báo.")
    food_stats = source_stats.get("food101", {})
    lines.extend(
        [
            "",
            "## Food-101 qua Hugging Face",
            "",
            "- Repo: <https://huggingface.co/datasets/ethz/food101>.",
            "- Bố cục đã xác minh: train **75.750 dòng / 3.798.520.995 byte / 8 shard**; validation **25.250 dòng / 1.261.451.313 byte / 3 shard**; tổng cộng 11 shard.",
            f"- Phương thức lần chạy: `{food_stats.get('method', 'không chạy')}`; số dòng train đã quét: **{food_stats.get('rows_scanned', 0)}**.",
        ]
    )
    downloaded_shards = food_stats.get("downloaded_shards", [])
    if downloaded_shards:
        lines.extend(["- Các shard fallback đã dùng (byte lưu / byte mạng trong lần chạy):"])
        for shard in downloaded_shards:
            lines.append(
                f"  - `{shard['file']}`: {shard['stored_bytes']:,} / {shard['network_bytes_this_run']:,} byte."
            )
    else:
        lines.append("- Không tải nguyên shard Parquet nào; dùng streaming và dừng khi các lớp Food-101 đạt cap.")
    lines.extend(
        [
            "",
            "### Ràng buộc quyền Food-101",
            "",
            "Ảnh Food-101 đến từ **Foodspotting** và **không thuộc sở hữu ETHZ**. Dataset card chỉ cho phép phạm vi scientific fair use; mọi sử dụng vượt phạm vi đó phải thương lượng với chủ ảnh theo điều khoản Foodspotting. Bộ dữ liệu này được chuẩn bị cho **bài tập/dự án học thuật, nghiên cứu khoa học**. Dự án **không được tuyên bố giấy phép mở bao trùm** cho ảnh Food-101 và không nên phát hành lại ảnh như một bộ open data.",
            "",
            "## Wikimedia Commons",
            "",
            f"- Ảnh Commons trong manifest: **{by_source['commons']}**; ảnh Food-101: **{by_source['food101']}**.",
            "- Collector dùng allow-list CC0, CC BY, CC BY-SA và Public domain; attribution/licence URL của từng tệp nằm trong cột `licence/source note`.",
            "- Category Commons có thể lẫn ảnh nhà hàng, nguyên liệu hoặc biến thể; cần duyệt thủ công trước khi huấn luyện chính thức.",
            "",
            "## Ánh xạ lớp và giới hạn nhãn",
            "",
            "Ánh xạ máy đọc được nằm tại `training/image/class_map.json`. Bốn lớp Food-101 phủ chính xác là `pizza`, `hamburger`, `sushi`, `steak`; các ánh xạ khác là gần đúng hoặc không được Food-101 phủ. Các món Việt dùng ảnh Commons và cần duyệt contact sheet trước khi huấn luyện.",
            "",
            "## Tệp đầu ra",
            "",
            "- `data/raw/images/<our_class_name>/*.jpg`: ảnh đã chuẩn hóa.",
            "- `data/processed/image_dataset_manifest.csv`: manifest dùng để trainer đọc split; không dùng `ImageFolder` để tự chia.",
            "- `data/processed/image_dataset_run.json`: thống kê phương thức tải và lỗi xử lý của lần chạy.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cap", type=int, default=DEFAULT_CAP, help="maximum final images per class")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="deterministic stratified split seed")
    parser.add_argument(
        "--minimum-trainable",
        type=int,
        default=DEFAULT_MINIMUM_TRAINABLE,
        help="count threshold used only for the too-few section of the report",
    )
    parser.add_argument(
        "--source",
        choices=("all", "food101", "commons"),
        default="all",
        help="source subset to prepare (all is required for the complete 15-class manifest)",
    )
    args = parser.parse_args(argv)
    if args.cap < 1 or args.cap > DEFAULT_CAP:
        parser.error(f"--cap must be between 1 and {DEFAULT_CAP}")
    if args.minimum_trainable < 1:
        parser.error("--minimum-trainable must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mapping = load_class_map()
    RAW_IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)
    seen_identities: set[str] = set()
    records: list[dict[str, Any]] = []
    source_stats: dict[str, Any] = {}
    started = time.time()
    if args.source in {"all", "food101"}:
        food_records, food_stats = collect_food101(mapping, args.cap, seen_identities)
        records.extend(food_records)
        source_stats["food101"] = food_stats
    if args.source in {"all", "commons"}:
        commons_records, commons_stats = collect_commons(mapping, args.cap, seen_identities)
        records.extend(commons_records)
        source_stats["commons"] = commons_stats
    records = assign_splits(records, args.seed)
    write_manifest(records)
    run_metadata = {
        "cap": args.cap,
        "seed": args.seed,
        "minimum_trainable": args.minimum_trainable,
        "source_selection": args.source,
        "elapsed_seconds": round(time.time() - started, 3),
        "record_count": len(records),
        "jpeg_bytes": sum(int(item["bytes"]) for item in records),
        "per_class_counts": dict(sorted(Counter(item["our_class"] for item in records).items())),
        "per_split_counts": dict(sorted(Counter(item["split"] for item in records).items())),
        "source_stats": source_stats,
    }
    RUN_METADATA_PATH.write_text(
        json.dumps(run_metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_report(records, mapping, args.cap, args.seed, args.minimum_trainable, source_stats)
    print(json.dumps(run_metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
