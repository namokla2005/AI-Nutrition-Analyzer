from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[2] / "scripts" / "collect_vn_images.py"


def load_module():
    spec = importlib.util.spec_from_file_location("collect_vn_images", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_search_uses_full_text_file_namespace_and_continuation(monkeypatch):
    module = load_module()
    calls = []

    def fake_api_get(params):
        calls.append(params)
        if len(calls) == 1:
            return {
                "query": {"pages": [{"pageid": 1, "title": "File:Pho.jpg", "imageinfo": [{}]}]},
                "continue": {"gsroffset": 50, "continue": "gsroffset||"},
            }
        return {"query": {"pages": [{"pageid": 2, "title": "File:Pho2.jpg", "imageinfo": [{}]}]}}

    monkeypatch.setattr(module, "api_get", fake_api_get)
    pages = list(module.iter_search_files("phở bò"))

    assert [page["pageid"] for page in pages] == [1, 2]
    assert calls[0]["generator"] == "search"
    assert calls[0]["gsrnamespace"] == 6
    assert calls[0]["gsrsearch"] == "phở bò"
    assert calls[1]["gsroffset"] == 50


def test_candidate_filter_requires_free_raster_large_and_food_relevant():
    module = load_module()
    good = {
        "license": "CC BY-SA 4.0",
        "copyrighted": "True",
        "mime_type": "image/jpeg",
        "width": 800,
        "height": 600,
        "file_title": "File:Phở bò Hà Nội.jpg",
        "description": "A bowl of Vietnamese beef pho",
    }
    assert module.candidate_rejection_reason(good, "phở bò") is None
    assert module.candidate_rejection_reason({**good, "width": 399}, "phở bò") == "too_small"
    assert module.candidate_rejection_reason({**good, "mime_type": "application/pdf"}, "phở bò") == "non_image"
    assert module.candidate_rejection_reason({**good, "mime_type": "image/svg+xml"}, "phở bò") == "quality_filter"
    assert module.candidate_rejection_reason({**good, "license": "All rights reserved"}, "phở bò") == "nonfree"
    assert module.candidate_rejection_reason({**good, "file_title": "File:Pho restaurant logo.svg"}, "phở bò") == "excluded_subject"


def test_search_class_specs_support_multiple_terms():
    module = load_module()
    assert module.parse_search_spec("nem_ran=nem rán|chả giò") == ("nem_ran", ["nem rán", "chả giò"])


def test_search_requests_categories_for_relevance_gate(monkeypatch):
    module = load_module()
    calls = []

    def fake_api_get(params):
        calls.append(params)
        return {"query": {"pages": []}}

    monkeypatch.setattr(module, "api_get", fake_api_get)
    list(module.iter_search_files("bánh cuốn"))

    assert calls[0]["prop"] == "imageinfo|categories"
    assert calls[0]["cllimit"] == "max"


def test_relevance_gate_requires_whole_phrase_in_filename_or_category():
    module = load_module()
    base = {
        "license": "CC BY-SA 4.0", "copyrighted": "True", "mime_type": "image/jpeg",
        "width": 800, "height": 600, "description": "search result text mentions bánh cuốn",
        "categories": [],
    }
    exact_filename = {**base, "file_title": "File:Banh cuon Ha Noi.jpg"}
    category_match = {
        **base, "file_title": "File:Breakfast 2024.jpg", "categories": ["Category:Bánh cuốn"],
    }
    substring_only = {**base, "file_title": "File:banhcuon-like text.jpg"}

    assert module.candidate_rejection_reason(exact_filename, ["bánh cuốn"], "banh_cuon") is None
    assert module.candidate_rejection_reason(category_match, ["bánh cuốn"], "banh_cuon") is None
    assert module.candidate_rejection_reason(substring_only, ["bánh cuốn"], "banh_cuon") == "term_mismatch"


def test_xoi_gate_rejects_vehicle_plate_and_raspberry_or_flower():
    module = load_module()
    base = {
        "license": "CC BY 4.0", "copyrighted": "True", "mime_type": "image/jpeg",
        "width": 800, "height": 600, "description": "", "categories": [],
    }
    assert module.candidate_rejection_reason(
        {**base, "file_title": "File:Belfast Citybus bus 2526 (XOI 2526).jpg"}, ["xôi"], "xoi"
    ) == "excluded_subject"
    assert module.candidate_rejection_reason(
        {**base, "file_title": "File:Cúc mâm xôi.jpg"}, ["xôi"], "xoi"
    ) == "excluded_subject"
    assert module.candidate_rejection_reason(
        {**base, "file_title": "File:Mâm xôi chín.jpg", "categories": ["Category:Raspberries"]}, ["xôi"], "xoi"
    ) == "excluded_subject"
    assert module.candidate_rejection_reason(
        {**base, "file_title": "File:Xôi gấc.jpg", "categories": ["Category:Xôi"]}, ["xôi"], "xoi"
    ) is None


def test_provenance_includes_acceptance_reason(tmp_path: Path):
    module = load_module()
    output = tmp_path / "images"
    reports = tmp_path / "reports"
    class_dir = output / "pho_ga"
    class_dir.mkdir(parents=True)
    image = class_dir / "commons_123.jpg"
    image.write_bytes(b"image bytes")
    image.with_suffix(".json").write_text(
        '{"original_filename":"Pho ga.jpg","acceptance_reason":"filename_keyword"}', encoding="utf-8"
    )

    rows = module.write_provenance(output, reports, ["pho_ga"])

    assert rows[0]["acceptance_reason"] == "filename_keyword"
    assert "acceptance_reason" in (reports / "commons_provenance.csv").read_text(encoding="utf-8-sig").splitlines()[0]


def test_audit_moves_irrelevant_existing_image_and_sidecar(tmp_path: Path):
    module = load_module()
    output = tmp_path / "images"
    class_dir = output / "xoi"
    class_dir.mkdir(parents=True)
    image = class_dir / "commons_99.jpg"
    sidecar = image.with_suffix(".json")
    image.write_bytes(b"not really an image")
    sidecar.write_text(
        '{"page_id":99,"original_filename":"Belfast Citybus (XOI 2526).jpg",'
        '"file_title":"File:Belfast Citybus (XOI 2526).jpg","license":"CC BY 4.0",'
        '"copyrighted":"True","mime_type":"image/jpeg","width":800,"height":600,"categories":[]}',
        encoding="utf-8",
    )

    result = module.audit_existing_class("xoi", ["xôi"], output)

    assert result["clean"] == 0
    assert result["rejected"] == 1
    assert not image.exists()
    assert (output / "_rejected" / "xoi" / image.name).exists()
    assert result["rejection_rows"][0]["reason"] == "excluded_subject"
