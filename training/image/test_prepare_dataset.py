from __future__ import annotations

import csv
import hashlib
import importlib.util
from collections import Counter
from pathlib import Path

import pytest
from PIL import Image

MODULE_PATH = Path(__file__).with_name("prepare_dataset.py")


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_dataset", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resize_to_jpeg_caps_long_side_and_converts_rgb(tmp_path: Path):
    module = load_module()
    source = tmp_path / "source.png"
    target = tmp_path / "target.jpg"
    Image.new("RGBA", (1200, 600), (255, 0, 0, 128)).save(source)

    width, height, size = module.resize_to_jpeg(source, target, max_side=512, quality=85)

    assert (width, height) == (512, 256)
    assert size == target.stat().st_size
    with Image.open(target) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"
        assert max(image.size) <= 512


def test_assign_splits_is_deterministic_stratified_and_disjoint():
    module = load_module()
    records = []
    for class_name in ("pizza", "sushi"):
        for index in range(20):
            records.append(
                {
                    "our_class": class_name,
                    "identity": hashlib.sha256(f"{class_name}-{index}".encode()).hexdigest(),
                    "relative_path": f"data/raw/images/{class_name}/{index}.jpg",
                }
            )

    first = module.assign_splits(records, seed=1234)
    second = module.assign_splits(records, seed=1234)

    assert [(row["relative_path"], row["split"]) for row in first] == [
        (row["relative_path"], row["split"]) for row in second
    ]
    assert len({row["identity"] for row in first}) == len(first)
    counts = Counter((row["our_class"], row["split"]) for row in first)
    for class_name in ("pizza", "sushi"):
        assert counts[(class_name, "train")] == 14
        assert counts[(class_name, "val")] == 3
        assert counts[(class_name, "test")] == 3


def test_write_manifest_uses_required_columns(tmp_path: Path):
    module = load_module()
    path = tmp_path / "manifest.csv"
    row = {
        "our_class": "pizza",
        "source_class": "pizza",
        "source": "food101",
        "split": "train",
        "relative_path": "data/raw/images/pizza/example.jpg",
        "width": 512,
        "height": 384,
        "bytes": 12345,
        "licence/source note": "Food-101 scientific fair use only",
        "identity": "not-written",
    }

    module.write_manifest([row], path)

    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == module.MANIFEST_COLUMNS
        assert list(reader)[0]["our_class"] == "pizza"


def test_class_map_has_all_targets_and_uses_commons_for_vietnamese_dishes():
    module = load_module()
    mapping = module.load_class_map(Path(__file__).with_name("class_map.json"))

    assert len(mapping) == 29
    assert {item["our_class"] for item in mapping} == module.TARGET_CLASSES
    commons_classes = {item["our_class"] for item in mapping if item["selected_source"] == "commons"}
    assert commons_classes == {
        "pho_bo", "bun_bo_hue", "banh_mi", "com_tam", "goi_cuon", "banh_xeo", "bun_cha",
        "xoi", "pho_ga", "banh_cuon", "hu_tieu", "mi_quang", "cha_ca", "nem_ran",
        "canh_chua", "banh_chung", "banh_khot", "bun_rieu", "banh_beo",
        "bun_dau_mam_tom", "bun_thit_nuong",
    }
    assert all(item["coverage_type"] in {"exact", "approximate", "not_covered"} for item in mapping)
    assert all(item.get("search_term") for item in mapping if item["our_class"] in commons_classes)


def test_rejects_duplicate_image_identity_across_splits():
    module = load_module()
    duplicate = "same-image"
    records = [
        {"our_class": "pizza", "identity": duplicate, "relative_path": "a.jpg"},
        {"our_class": "sushi", "identity": duplicate, "relative_path": "b.jpg"},
    ]

    with pytest.raises(ValueError, match="Trùng định danh ảnh"):
        module.assign_splits(records, seed=1)
