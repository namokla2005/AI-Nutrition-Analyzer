#!/usr/bin/env python3
"""Apply visual review, build provenance, reviewed sheets, and verify round 3."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT / "data" / "raw" / "images"
REPORTS = PROJECT / "data" / "reports"
CLASSES = ["ca_kho_to", "com_ga", "xoi_xeo", "che_ba_mau"]
REJECT_INDICES = {
    "ca_kho_to": [1,2,3,4,5,7,8,9,11,12,13,14,16,18,20,22,23,24,25,26,27,28,29,33,42,45,51,54,58,65,66,71,72,75],
    "com_ga": [1,2,8,9,12,13,14,15,16,19,22,23,25,26,27,28,29,30,31,33,35,36,37,40,41,42,43,44,45,46,48,49,50,52,53,55,56,57,58,59,73,76,77,78],
    "xoi_xeo": [1,2,3,4,5,6,10,16,17,21,34,41,43,44,49,50,51,55,57,65,70,74],
    "che_ba_mau": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,17,19,24,26,27,28,34,37,38,43,47,48,60,63,65,70,71,74],
}
REASON = "Visual review: wrong dish, non-food/people/sign/graphic, or unsuitable for this class"
REQUIRED = ["id", "title", "url", "foreign_landing_url", "creator", "license", "license_url", "provider", "source", "width", "height", "sha256", "our_class", "query"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def initial_mapping() -> dict[str, list[str]]:
    mapping_path = REPORTS / "round3_visual_review_mapping.json"
    if mapping_path.exists():
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
        return {key: list(value) for key, value in data.items()}
    mapping = {class_name: [path.name for path in sorted((ROOT / class_name).glob("*.jpg"))] for class_name in CLASSES}
    for class_name, names in mapping.items():
        if len(names) != 80:
            raise AssertionError(f"{class_name}: expected 80 pre-review images, got {len(names)}")
    mapping_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return mapping


def apply_review(mapping: dict[str, list[str]]) -> list[dict]:
    decisions = []
    for class_name in CLASSES:
        reject_names = {mapping[class_name][index - 1] for index in REJECT_INDICES[class_name]}
        rejected_dir = ROOT / "_rejected" / class_name
        rejected_dir.mkdir(parents=True, exist_ok=True)
        for filename in mapping[class_name]:
            rejected = filename in reject_names
            source_image = ROOT / class_name / filename
            rejected_image = rejected_dir / filename
            if rejected and source_image.exists():
                shutil.move(str(source_image), rejected_image)
                source_json = source_image.with_suffix(".json")
                if source_json.exists():
                    shutil.move(str(source_json), rejected_image.with_suffix(".json"))
            image = rejected_image if rejected else source_image
            if not image.exists():
                raise AssertionError(f"missing reviewed image: {image}")
            sidecar = image.with_suffix(".json")
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            data["review_status"] = "rejected" if rejected else "accepted"
            data["local_file"] = image.relative_to(PROJECT).as_posix()
            if rejected:
                data["review_reason"] = REASON
            else:
                data.pop("review_reason", None)
            sidecar.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            decisions.append({"class": class_name, "file": filename, "review_status": data["review_status"], "reason": REASON if rejected else ""})
    (REPORTS / "round3_visual_review.json").write_text(json.dumps(decisions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return decisions


def build_provenance(mapping: dict[str, list[str]]) -> list[dict]:
    rows = []
    for class_name in CLASSES:
        for filename in mapping[class_name]:
            active = ROOT / class_name / filename
            rejected = ROOT / "_rejected" / class_name / filename
            image = active if active.exists() else rejected
            sidecar = image.with_suffix(".json")
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            data["local_file"] = image.relative_to(PROJECT).as_posix()
            data["review_status"] = "accepted" if active.exists() else "rejected"
            rows.append(data)
    json_path = REPORTS / "round3_provenance_new_vietnamese.json"
    csv_path = REPORTS / "round3_provenance_new_vietnamese.csv"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = list(dict.fromkeys([*REQUIRED, "local_file", "downloaded_from", "stored_width", "stored_height", "downloaded_bytes", "review_status", "review_reason"]))
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def build_reviewed_sheets(mapping: dict[str, list[str]]) -> list[str]:
    out_dir = REPORTS / "round3_contact_sheets_reviewed"
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for class_name in CLASSES:
        for old in out_dir.glob(f"{class_name}_*.jpg"):
            old.unlink()
        names = mapping[class_name]
        for page_no, start in enumerate(range(0, len(names), 25), 1):
            batch = names[start:start + 25]
            cw, ch, cols = 220, 184, 5
            rows = (len(batch) + cols - 1) // cols
            sheet = Image.new("RGB", (cw * cols, ch * rows), "white")
            draw = ImageDraw.Draw(sheet)
            for local_idx, filename in enumerate(batch):
                active = ROOT / class_name / filename
                rejected = ROOT / "_rejected" / class_name / filename
                is_rejected = not active.exists()
                path = rejected if is_rejected else active
                with Image.open(path) as source:
                    thumb = ImageOps.contain(source.convert("RGB"), (cw - 12, ch - 44))
                x, y = (local_idx % cols) * cw, (local_idx // cols) * ch
                sheet.paste(thumb, (x + (cw - thumb.width) // 2, y + 4))
                color = "#b00020" if is_rejected else "#087f23"
                label = ("LOAI " if is_rejected else "NHAN ") + f"{start + local_idx + 1:03d} {filename}"
                draw.rectangle((x + 1, y + 1, x + cw - 2, y + ch - 2), outline=color, width=3)
                draw.text((x + 5, y + ch - 34), label, fill=color)
            destination = out_dir / f"{class_name}_{page_no:02d}.jpg"
            sheet.save(destination, "JPEG", quality=92)
            made.append(destination.relative_to(PROJECT).as_posix())
    return made


def verify(mapping: dict[str, list[str]], rows: list[dict], decisions: list[dict], sheets: list[str]) -> dict:
    errors = []
    all_hashes: dict[str, list[str]] = defaultdict(list)
    class_rows = []
    for class_name in CLASSES:
        accepted = sorted((ROOT / class_name).glob("*.jpg"))
        rejected = sorted((ROOT / "_rejected" / class_name).glob("*.jpg"))
        downloaded = len(accepted) + len(rejected)
        for image in [*accepted, *rejected]:
            if not re.fullmatch(r"(?:ov|web)_[0-9a-f]{8}\.jpg|commons_\d+\.jpg", image.name):
                errors.append(f"invalid filename: {image}")
            if image.stat().st_size < 5 * 1024:
                errors.append(f"below 5KB: {image}")
            try:
                with Image.open(image) as source:
                    source.verify()
            except Exception as exc:
                errors.append(f"invalid image: {image}: {exc}")
            sidecar = image.with_suffix(".json")
            if not sidecar.exists():
                errors.append(f"missing sidecar: {image}")
                continue
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            missing = [field for field in REQUIRED if field not in data]
            if missing:
                errors.append(f"missing fields {missing}: {sidecar}")
            actual = digest(image)
            if data.get("sha256") != actual:
                errors.append(f"sha256 mismatch: {image}")
            all_hashes[actual].append(image.relative_to(PROJECT).as_posix())
        class_rows.append({
            "class": class_name,
            "downloaded_new": downloaded,
            "rejected": len(rejected),
            "accepted_new": len(accepted),
            "clean_total": len(accepted),
            "download_target_met": downloaded >= 40,
            "clean_target_met": len(accepted) >= 34,
        })
    duplicates = {key: value for key, value in all_hashes.items() if len(value) > 1}
    if duplicates:
        errors.append(f"duplicate content hashes: {len(duplicates)}")
    if len(rows) != 320:
        errors.append(f"provenance rows {len(rows)} != 320")
    if len(decisions) != 320:
        errors.append(f"review decisions {len(decisions)} != 320")
    for row in rows:
        path = PROJECT / row["local_file"]
        if not path.exists():
            errors.append(f"provenance missing file: {path}")
    source_counts = Counter(row.get("provider") or row.get("source") or "unknown" for row in rows)
    license_counts = Counter((row.get("license") or "unknown").lower() for row in rows)
    accepted_license_counts = Counter(
        (row.get("license") or "unknown").lower()
        for row in rows if row.get("review_status") == "accepted"
    )
    review_counts = Counter(row["review_status"] for row in rows)
    summary = {
        "classes": class_rows,
        "provenance_path": "data/reports/round3_provenance_new_vietnamese.json",
        "provenance_records": len(rows),
        "visual_review_records": len(decisions),
        "review_counts": dict(review_counts),
        "license_counts": dict(sorted(license_counts.items())),
        "accepted_license_counts": dict(sorted(accepted_license_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "duplicate_sha256_groups": len(duplicates),
        "reviewed_contact_sheets": sheets,
        "errors": errors,
        "verified": not errors and all(row["download_target_met"] and row["clean_target_met"] for row in class_rows),
    }
    (REPORTS / "round3_collection_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not summary["verified"]:
        raise AssertionError(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    mapping = initial_mapping()
    decisions = apply_review(mapping)
    rows = build_provenance(mapping)
    sheets = build_reviewed_sheets(mapping)
    summary = verify(mapping, rows, decisions, sheets)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
