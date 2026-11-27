#!/usr/bin/env python3
"""Collect permitted public-web fallback images through DuckDuckGo image search."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

from collect_round3_new_classes import PROJECT, ROOT, REPORTS, build_contact_sheets, download_paced, existing_state, save_item

QUERIES = {
    "ca_kho_to": ["cá kho tộ món ăn", "cá kho tộ niêu đất", "Vietnamese caramelized fish clay pot"],
    "com_ga": ["cơm gà món ăn", "cơm gà Hội An", "Vietnamese chicken rice plate"],
    "xoi_xeo": ["xôi xéo món ăn", "xôi xéo Hà Nội", "Vietnamese xoi xeo sticky rice"],
    "che_ba_mau": ["chè ba màu món ăn", "chè ba màu Việt Nam", "Vietnamese three color dessert che ba mau"],
}
UA = "Mozilla/5.0"


def search(client: httpx.Client, query: str) -> list[dict[str, Any]]:
    page = client.get("https://duckduckgo.com/", params={"q": query})
    page.raise_for_status()
    match = re.search(r"vqd=[\"']?([\d-]+)", page.text)
    if not match:
        return []
    response = client.get("https://duckduckgo.com/i.js", params={
        "l": "us-en", "o": "json", "q": query, "vqd": match.group(1),
        "f": ",,,", "p": "1",
    })
    response.raise_for_status()
    return response.json().get("results") or []


def collect(client: httpx.Client, class_name: str, target_total: int) -> dict[str, int]:
    class_dir = ROOT / class_name
    class_dir.mkdir(parents=True, exist_ok=True)
    ids, hashes = existing_state(class_name)
    known_urls = set()
    for base in (class_dir, ROOT / "_rejected" / class_name):
        for sidecar in base.glob("*.json") if base.exists() else []:
            try:
                known_urls.add(str(json.loads(sidecar.read_text(encoding="utf-8")).get("url") or ""))
            except (OSError, json.JSONDecodeError):
                pass
    stats = {"before": len(list(class_dir.glob("*.jpg"))), "candidates": 0, "saved": 0, "failed": 0, "duplicates": 0}
    for query in QUERIES[class_name]:
        if len(list(class_dir.glob("*.jpg"))) >= target_total:
            break
        try:
            results = search(client, query)
        except (httpx.HTTPError, ValueError):
            stats["failed"] += 1
            continue
        for row in results:
            if len(list(class_dir.glob("*.jpg"))) >= target_total:
                break
            stats["candidates"] += 1
            image_url = str(row.get("image") or "")
            landing_url = str(row.get("url") or "")
            if not image_url or image_url in known_urls:
                stats["duplicates"] += 1
                continue
            known_urls.add(image_url)
            item_id = hashlib.sha1(image_url.encode("utf-8")).hexdigest()
            if item_id in ids:
                stats["duplicates"] += 1
                continue
            ids.add(item_id)
            try:
                data, downloaded_from = download_paced(client, [image_url, str(row.get("thumbnail") or "")], landing_url)
                item = {
                    "id": item_id,
                    "title": row.get("title") or "",
                    "url": image_url,
                    "foreign_landing_url": landing_url,
                    "creator": "",
                    "license": "",
                    "license_url": "",
                    "provider": "DuckDuckGo Image Search",
                    "source": row.get("source") or "public_web",
                    "width": row.get("width"),
                    "height": row.get("height"),
                }
                if save_item(class_name, "web", item_id[:8], item, query, data, downloaded_from, hashes):
                    stats["saved"] += 1
                    print(json.dumps({"class": class_name, "source": "web", "saved": stats["saved"], "file": f"web_{item_id[:8]}.jpg", "query": query}, ensure_ascii=False), flush=True)
                else:
                    stats["duplicates"] += 1
            except (ValueError, OSError):
                stats["failed"] += 1
        time.sleep(1.0)
    stats["after"] = len(list(class_dir.glob("*.jpg")))
    return stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--classes", nargs="*", choices=sorted(QUERIES), default=list(QUERIES))
    parser.add_argument("--target-total", type=int, default=80)
    args = parser.parse_args()
    summaries = []
    with httpx.Client(headers={"User-Agent": UA}, timeout=httpx.Timeout(35.0, connect=15.0), follow_redirects=True) as client:
        for class_name in args.classes:
            result = collect(client, class_name, args.target_total)
            result["class"] = class_name
            summaries.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "round3_web_collection_stats.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"contact_sheets": build_contact_sheets(args.classes)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
