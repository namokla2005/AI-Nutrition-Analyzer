#!/usr/bin/env python3
"""Stream a bounded, import-ready subset from the Open Food Facts CSV dump.

The dump is read exactly once and never materialized on disk or in memory. The
selector retains at most 10,000 Vietnam-preferred rows and 20,000 balanced
fallback rows, then writes no more than --limit rows.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import math
import random
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Iterable, TextIO

DEFAULT_URL = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
USER_AGENT = "AI-Nutrition-Analyzer/1.0 (Open Food Facts bounded research subset)"
REQUIRED_NUTRIENTS = ("energy-kcal_100g", "proteins_100g", "carbohydrates_100g", "fat_100g")
OPTIONAL_NUTRIENTS = ("fiber_100g", "sugars_100g", "sodium_100g")
OUTPUT_FIELDS = (
    "code",
    "product_name",
    "brands",
    "countries_tags",
    "countries_en",
    "pnns_groups_1",
    "categories_en",
    *REQUIRED_NUTRIENTS,
    *OPTIONAL_NUTRIENTS,
)
MAX_CATEGORY_KEYS = 200


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="Gzipped OFF CSV/TSV dump URL")
    parser.add_argument("--input", type=Path, help="Optional local .gz dump (still streamed)")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=20_000)
    parser.add_argument("--vietnam-cap", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20261119)
    return parser.parse_args()


def clean_text(value: str | None) -> str:
    return (value or "").strip()


def numeric_text(value: str | None, field: str, required: bool) -> str | None:
    raw = clean_text(value)
    if not raw:
        return None
    try:
        number = float(raw)
    except ValueError:
        return None
    if not math.isfinite(number) or number < 0:
        return None
    if field != "energy-kcal_100g" and number > 100:
        return None
    if field == "energy-kcal_100g" and number > 10_000:
        return None
    # Normalize only the numeric representation; never substitute a missing value.
    return format(number, ".15g") if required or raw else raw


def is_vietnam(row: dict[str, str]) -> bool:
    text = f"{clean_text(row.get('countries_tags'))},{clean_text(row.get('countries_en'))}".lower()
    return "vietnam" in text or "việt nam" in text or "viet nam" in text


def category_for(row: dict[str, str], known: set[str]) -> str:
    pnns = clean_text(row.get("pnns_groups_1"))
    if pnns and pnns.lower() not in {"unknown", "not-applicable"}:
        candidate = f"PNNS: {pnns[:120]}"
    else:
        first = clean_text(row.get("categories_en")).split(",", 1)[0].strip()
        candidate = f"Category: {first[:120]}" if first else "Uncategorized"
    if candidate in known:
        return candidate
    if len(known) < MAX_CATEGORY_KEYS:
        known.add(candidate)
        return candidate
    return "Other categories"


def project_row(row: dict[str, str]) -> dict[str, str] | None:
    result = {field: clean_text(row.get(field)) for field in OUTPUT_FIELDS}
    for field in REQUIRED_NUTRIENTS:
        parsed = numeric_text(row.get(field), field, required=True)
        if parsed is None:
            return None
        result[field] = parsed
    for field in OPTIONAL_NUTRIENTS:
        parsed = numeric_text(row.get(field), field, required=False)
        result[field] = parsed or ""
    return result


def reservoir_add(pool: list[dict[str, str]], item: dict[str, str], seen: int, cap: int, rng: random.Random) -> None:
    if cap <= 0:
        return
    if len(pool) < cap:
        pool.append(item)
    else:
        index = rng.randrange(seen)
        if index < cap:
            pool[index] = item


def balanced_add(
    buckets: dict[str, list[dict[str, str]]],
    seen: Counter[str],
    category: str,
    item: dict[str, str],
    cap: int,
    total: int,
    rng: random.Random,
) -> int:
    seen[category] += 1
    if total < cap:
        buckets[category].append(item)
        return total + 1

    largest = max(buckets, key=lambda key: (len(buckets[key]), key))
    if len(buckets[category]) < len(buckets[largest]):
        victim_index = rng.randrange(len(buckets[largest]))
        buckets[largest].pop(victim_index)
        if not buckets[largest]:
            del buckets[largest]
        buckets[category].append(item)
        return total

    current = buckets[category]
    if current:
        index = rng.randrange(seen[category])
        if index < len(current):
            current[index] = item
    return total


def detect_delimiter(header: str) -> str:
    # Current OFF export is tab-delimited; older mirrors/documentation may differ.
    return "\t" if header.count("\t") >= header.count(";") else ";"


def open_source(args: argparse.Namespace) -> tuple[BinaryIO, str, int | None]:
    if args.input:
        stream = args.input.open("rb")
        return stream, str(args.input.resolve()), args.input.stat().st_size
    request = urllib.request.Request(args.url, headers={"User-Agent": USER_AGENT})
    response = urllib.request.urlopen(request, timeout=120)
    length_text = response.headers.get("Content-Length")
    length = int(length_text) if length_text and length_text.isdigit() else None
    return response, response.geturl(), length


def primary_country(row: dict[str, str]) -> str:
    countries = clean_text(row.get("countries_en"))
    if countries:
        return countries.split(",", 1)[0].strip()
    tags = clean_text(row.get("countries_tags"))
    return tags.split(",", 1)[0].strip() if tags else "Unknown"


def write_outputs(output_dir: Path, rows: list[dict[str, str]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "off_subset.csv"
    jsonl_path = output_dir / "off_subset.jsonl"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def extract(args: argparse.Namespace) -> dict[str, object]:
    if args.limit <= 0 or args.vietnam_cap < 0:
        raise ValueError("--limit must be positive and --vietnam-cap non-negative")

    rng = random.Random(args.seed)
    vietnam_pool: list[dict[str, str]] = []
    balanced_buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    balanced_total = 0
    category_seen: Counter[str] = Counter()
    known_categories: set[str] = set()
    rows_read = 0
    eligible_rows = 0
    vietnam_seen = 0
    started = datetime.now(timezone.utc)

    raw, resolved_url, content_length = open_source(args)
    csv.field_size_limit(sys.maxsize)
    try:
        with gzip.GzipFile(fileobj=raw, mode="rb") as gz:
            text = io.TextIOWrapper(gz, encoding="utf-8", errors="replace", newline="")
            header = text.readline()
            if not header:
                raise RuntimeError("The compressed export has no header")
            delimiter = detect_delimiter(header)
            reader = csv.DictReader(IterableWithHeader(header, text), delimiter=delimiter)
            missing = [field for field in REQUIRED_NUTRIENTS if field not in (reader.fieldnames or [])]
            if missing:
                raise RuntimeError(f"Required columns missing: {', '.join(missing)}")
            for source_row in reader:
                rows_read += 1
                selected = project_row(source_row)
                if selected is None:
                    continue
                eligible_rows += 1
                category = category_for(source_row, known_categories)
                selected["_selection_category"] = category
                if is_vietnam(source_row):
                    vietnam_seen += 1
                    reservoir_add(vietnam_pool, selected, vietnam_seen, args.vietnam_cap, rng)
                else:
                    balanced_total = balanced_add(
                        balanced_buckets,
                        category_seen,
                        category,
                        selected,
                        args.limit,
                        balanced_total,
                        rng,
                    )
    finally:
        raw.close()

    vietnam_pool.sort(key=lambda row: (row.get("code", ""), row.get("product_name", "")))
    fallback = [row for values in balanced_buckets.values() for row in values]
    fallback.sort(key=lambda row: (row["_selection_category"], row.get("code", ""), row.get("product_name", "")))
    kept = vietnam_pool[: args.limit]
    kept.extend(fallback[: max(0, args.limit - len(kept))])

    kept_by_category = Counter(row.pop("_selection_category") for row in kept)
    kept_by_country = Counter(primary_country(row) for row in kept)
    kept_vietnam = sum(1 for row in kept if is_vietnam(row))
    macro_complete = sum(all(clean_text(row.get(field)) for field in REQUIRED_NUTRIENTS) for row in kept)
    write_outputs(args.output_dir, kept)

    finished = datetime.now(timezone.utc)
    metadata: dict[str, object] = {
        "extraction_path": "streamed_bulk_csv_dump",
        "source_url": args.url if not args.input else str(args.input.resolve()),
        "resolved_url": resolved_url,
        "fetched_content_length_bytes": content_length,
        "extraction_started_utc": started.isoformat(),
        "extraction_finished_utc": finished.isoformat(),
        "delimiter": "tab" if delimiter == "\t" else "semicolon",
        "random_seed": args.seed,
        "output_limit": args.limit,
        "vietnam_reservoir_cap": args.vietnam_cap,
        "rows_read": rows_read,
        "eligible_rows": eligible_rows,
        "rows_kept": len(kept),
        "kept_vietnam": kept_vietnam,
        "eligible_vietnam_rows_seen": vietnam_seen,
        "kept_with_all_four_macros": macro_complete,
        "kept_by_country_primary_label": dict(sorted(kept_by_country.items())),
        "kept_by_selection_category": dict(sorted(kept_by_category.items())),
    }
    metadata_path = args.output_dir / "extraction_metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


class IterableWithHeader:
    """Put an already-read header back in front of a text iterator."""

    def __init__(self, header: str, rest: TextIO) -> None:
        self.header = header
        self.rest = rest
        self.used = False

    def __iter__(self) -> "IterableWithHeader":
        return self

    def __next__(self) -> str:
        if not self.used:
            self.used = True
            return self.header
        return next(self.rest)


if __name__ == "__main__":
    try:
        result = extract(parse_args())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
    print(json.dumps(result, ensure_ascii=False, indent=2))
