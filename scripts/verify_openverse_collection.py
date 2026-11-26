#!/usr/bin/env python3
"""Verify the Openverse image batch without rebuilding the training manifest."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

PROJECT = Path(__file__).resolve().parents[1]
CLASSES = ["canh_chua", "banh_beo", "banh_khot", "bun_dau_mam_tom", "bun_rieu", "bun_thit_nuong", "pho_ga"]
BEFORE = {"canh_chua": 5, "banh_beo": 12, "banh_khot": 22, "bun_dau_mam_tom": 10, "bun_rieu": 15, "bun_thit_nuong": 12, "pho_ga": 10}
ALLOWED = {"cc0", "by", "by-sa", "pdm", "public-domain", "public domain"}
root = PROJECT / "data" / "raw" / "images"
reports = PROJECT / "data" / "reports"
provenance_path = reports / "openverse_provenance.json"
review_path = reports / "openverse_visual_review.json"
rows = json.loads(provenance_path.read_text(encoding="utf-8"))
review = json.loads(review_path.read_text(encoding="utf-8"))

missing_license_or_url = 0
invalid_license = 0
missing_required_fields = 0
missing_files = 0
bad_dimensions = []
for row in rows:
    if not row.get("license") or not row.get("url") or not row.get("foreign_landing_url") or not row.get("license_url"):
        missing_license_or_url += 1
    license_name = str(row.get("license") or "").lower()
    if license_name not in ALLOWED or "nc" in license_name or "nd" in license_name:
        invalid_license += 1
    if any(field not in row for field in ("id", "title", "url", "thumbnail", "foreign_landing_url", "creator", "license", "license_version", "license_url", "provider", "source", "width", "height", "filesize")):
        missing_required_fields += 1
    image = PROJECT / row["local_file"]
    if not image.exists():
        missing_files += 1
        continue
    with Image.open(image) as source:
        width, height = source.size
        if source.format != "JPEG" or max(width, height) > 512:
            bad_dimensions.append(row["local_file"])

# Exact-content duplicate check against every image already present in each active class.
def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

duplicate_active_sha256 = {}
for class_name in CLASSES:
    by_hash = defaultdict(list)
    for image in (root / class_name).glob("*"):
        if image.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp"}:
            by_hash[digest(image)].append(image.name)
    duplicates = [names for names in by_hash.values() if len(names) > 1]
    if duplicates:
        duplicate_active_sha256[class_name] = duplicates

summary_rows = []
for class_name in CLASSES:
    clean_new = len(list((root / class_name).glob("ov_*.jpg")))
    rejected = len(list((root / "_rejected" / class_name).glob("ov_*.jpg")))
    downloaded = clean_new + rejected
    summary_rows.append({
        "class": class_name,
        "before": BEFORE[class_name],
        "downloaded_new": downloaded,
        "rejected": rejected,
        "clean_new": clean_new,
        "clean_final": BEFORE[class_name] + clean_new,
        "target_met": BEFORE[class_name] + clean_new >= 34,
    })

review_counts = Counter(row["lớp"] for row in review)
review_matches_rejected = all(
    review_counts[class_name] == next(row["rejected"] for row in summary_rows if row["class"] == class_name)
    for class_name in CLASSES
)
contact_sheets = sorted(path.relative_to(PROJECT).as_posix() for path in (reports / "openverse_contact_sheets_reviewed").glob("*.jpg"))
summary = {
    "classes": summary_rows,
    "provenance_records": len(rows),
    "provenance_physical_lines": sum(1 for _ in provenance_path.open(encoding="utf-8")),
    "provenance_csv_records": sum(1 for _ in csv.DictReader((reports / "openverse_provenance.csv").open(encoding="utf-8-sig", newline=""))),
    "visual_review_records": len(review),
    "missing_license_or_url": missing_license_or_url,
    "invalid_license": invalid_license,
    "missing_required_fields": missing_required_fields,
    "missing_files": missing_files,
    "bad_jpeg_or_long_edge": bad_dimensions,
    "duplicate_active_sha256": duplicate_active_sha256,
    "review_matches_rejected": review_matches_rejected,
    "contact_sheets": contact_sheets,
}
assert len(rows) == sum(row["downloaded_new"] for row in summary_rows)
assert summary["provenance_csv_records"] == len(rows)
assert missing_license_or_url == invalid_license == missing_required_fields == missing_files == 0
assert not bad_dimensions
assert not duplicate_active_sha256
assert review_matches_rejected
(reports / "openverse_collection_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
