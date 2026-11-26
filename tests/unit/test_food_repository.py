"""Kiểm thử tìm kiếm thực phẩm trên SQLite thật (in-memory), gồm tìm không dấu."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.utils import normalize_name, strip_diacritics
from app.models import Base, Food, FoodAlias, FoodSource, Nutrient
from app.repositories.food_repository import FoodRepository


@pytest.fixture()
def db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def seeded(db: Session) -> Session:
    src = FoodSource(code="test_src", name="Nguồn kiểm thử", kind="manual")
    db.add(src)
    db.flush()

    db.add_all(
        [
            Food(
                source_id=src.id,
                source_ref="1",
                name_vi="Phở bò",
                name_en="Beef pho",
                name_normalized=normalize_name("Phở bò"),
                category="Món nước",
                cooking_state="cooked",
                energy_kcal_per_100g=95.0,
            ),
            Food(
                source_id=src.id,
                source_ref="2",
                name_vi="Cơm trắng chín",
                name_en="Cooked white rice",
                name_normalized=normalize_name("Cơm trắng chín"),
                category="Ngũ cốc",
                cooking_state="cooked",
                energy_kcal_per_100g=130.0,
            ),
            Food(
                source_id=src.id,
                source_ref="3",
                name_vi="Ức gà nướng",
                name_en="Grilled chicken breast",
                name_normalized=normalize_name("Ức gà nướng"),
                category="Thịt",
                cooking_state="cooked",
                energy_kcal_per_100g=165.0,
            ),
            Food(
                source_id=src.id,
                source_ref="4",
                name_vi="Gạo trắng sống",
                name_en="Raw white rice",
                name_normalized=normalize_name("Gạo trắng sống"),
                category="Ngũ cốc",
                cooking_state="raw",
                energy_kcal_per_100g=360.0,
            ),
        ]
    )
    db.commit()
    return db


def _names(rows: list[Food]) -> set[str]:
    return {f.name_vi for f in rows}


class TestDiacritics:
    def test_bo_dau_tieng_viet(self):
        assert strip_diacritics("Phở bò") == "Pho bo"
        assert strip_diacritics("Bún bò Huế") == "Bun bo Hue"
        assert strip_diacritics("Bánh xèo") == "Banh xeo"

    def test_chu_d_gach_ngang(self):
        assert strip_diacritics("Đường") == "Duong"

    def test_chuan_hoa_khoa_tim_kiem(self):
        assert normalize_name("  Phở   BÒ!!! ") == "pho bo"
        assert normalize_name("Cơm tấm (Sài Gòn)") == "com tam sai gon"


class TestSearch:
    def test_tim_khong_dau_van_ra_ket_qua(self, seeded: Session):
        repo = FoodRepository(seeded)
        rows, total = repo.search(query="pho bo")
        assert total == 1
        assert _names(rows) == {"Phở bò"}

    def test_tim_co_dau_van_ra_ket_qua(self, seeded: Session):
        repo = FoodRepository(seeded)
        rows, _ = repo.search(query="Phở bò")
        assert _names(rows) == {"Phở bò"}

    def test_tim_mot_phan_tu(self, seeded: Session):
        repo = FoodRepository(seeded)
        rows, _ = repo.search(query="ga nuong")
        assert _names(rows) == {"Ức gà nướng"}

    def test_loc_theo_trang_thai_che_bien(self, seeded: Session):
        repo = FoodRepository(seeded)
        cooked, total_cooked = repo.search(cooking_state="cooked")
        raw, total_raw = repo.search(cooking_state="raw")
        assert total_cooked == 3
        assert total_raw == 1
        assert _names(raw) == {"Gạo trắng sống"}

    def test_loc_theo_nhom(self, seeded: Session):
        repo = FoodRepository(seeded)
        rows, total = repo.search(category="Ngũ cốc")
        assert total == 2
        assert _names(rows) == {"Cơm trắng chín", "Gạo trắng sống"}

    def test_loc_theo_khoang_calo(self, seeded: Session):
        repo = FoodRepository(seeded)
        rows, total = repo.search(min_kcal=100.0, max_kcal=200.0)
        assert total == 2
        assert _names(rows) == {"Cơm trắng chín", "Ức gà nướng"}

    def test_phan_trang(self, seeded: Session):
        repo = FoodRepository(seeded)
        page1, total = repo.search(limit=2, offset=0)
        page2, _ = repo.search(limit=2, offset=2)
        assert total == 4
        assert len(page1) == 2
        assert len(page2) == 2
        assert not (_names(page1) & _names(page2))

    def test_khong_tim_thay_tra_ve_rong(self, seeded: Session):
        repo = FoodRepository(seeded)
        rows, total = repo.search(query="món không tồn tại xyz")
        assert rows == []
        assert total == 0

    def test_gioi_han_limit_toi_da_100(self, seeded: Session):
        repo = FoodRepository(seeded)
        rows, _ = repo.search(limit=9999)
        assert len(rows) == 4  # chỉ có 4 bản ghi, và limit bị kẹp về 100


class TestNutrientsAndSync:
    def test_dong_bo_nang_luong_tu_bang_chat_dinh_duong(self, seeded: Session):
        repo = FoodRepository(seeded)
        food = seeded.query(Food).filter(Food.source_ref == "1").one()
        nutrient = Nutrient(code="energy_kcal", name_vi="Năng lượng", name_en="Energy", unit="kcal", is_energy=1)
        seeded.add(nutrient)
        seeded.flush()

        repo.upsert_nutrient(food.id, nutrient.id, 97.5, "kcal", quality="measured")
        seeded.commit()
        assert repo.sync_energy_cache(food.id) == pytest.approx(97.5)
        assert food.energy_kcal_per_100g == pytest.approx(97.5)

    def test_chat_thieu_luu_la_none(self, seeded: Session):
        repo = FoodRepository(seeded)
        food = seeded.query(Food).filter(Food.source_ref == "2").one()
        nutrient = Nutrient(code="sugar_g", name_vi="Đường", name_en="Sugars", unit="g")
        seeded.add(nutrient)
        seeded.flush()
        repo.upsert_nutrient(food.id, nutrient.id, None, "g")
        seeded.commit()

        values = repo.nutrient_values_per_100g(food.id)
        assert values["sugar_g"] is None  # KHÔNG được biến thành 0

    def test_upsert_khong_tao_ban_ghi_trung(self, seeded: Session):
        repo = FoodRepository(seeded)
        food = seeded.query(Food).filter(Food.source_ref == "3").one()
        nutrient = Nutrient(code="fat_g", name_vi="Chất béo", name_en="Fat", unit="g")
        seeded.add(nutrient)
        seeded.flush()
        repo.upsert_nutrient(food.id, nutrient.id, 3.6, "g")
        seeded.commit()
        repo.upsert_nutrient(food.id, nutrient.id, 3.8, "g")
        seeded.commit()

        from app.models import FoodNutrient

        rows = seeded.query(FoodNutrient).filter(
            FoodNutrient.food_id == food.id, FoodNutrient.nutrient_id == nutrient.id
        ).all()
        assert len(rows) == 1
        assert rows[0].amount_per_100g == pytest.approx(3.8)


class TestAliases:
    def test_them_ten_goi_khac_va_tim_duoc(self, seeded: Session):
        repo = FoodRepository(seeded)
        food = seeded.query(Food).filter(Food.source_ref == "1").one()
        repo.add_alias(food.id, "Phở")
        repo.add_alias(food.id, "Pho")
        seeded.commit()

        rows, total = repo.search(query="pho")
        assert total == 1
        assert _names(rows) == {"Phở bò"}

    def test_khong_them_alias_trung(self, seeded: Session):
        repo = FoodRepository(seeded)
        food = seeded.query(Food).filter(Food.source_ref == "1").one()
        repo.add_alias(food.id, "Phở Bò")
        repo.add_alias(food.id, "pho bo")
        seeded.commit()
        assert len(repo.aliases(food.id)) == 1


class TestXepHangKetQua:
    """Dữ liệu thật có nhiều bản ghi tên không đọc được / không có tên — phải nằm cuối."""

    @pytest.fixture()
    def seeded_messy(self, seeded: Session) -> Session:
        src = seeded.query(FoodSource).first()
        seeded.add_all(
            [
                Food(  # tên Kirin -> normalize_name chỉ còn "0"
                    source_id=src.id,
                    source_ref="bio",
                    name_en="Бира Пиринско 0%",
                    name_normalized=normalize_name("Бира Пиринско 0%"),
                    energy_kcal_per_100g=14.0,
                ),
                Food(  # không có tên nào cả
                    source_id=src.id,
                    source_ref="noname",
                    name_en="",
                    name_normalized="",
                    energy_kcal_per_100g=560.0,
                ),
                Food(  # tên đọc được nhưng THIẾU năng lượng
                    source_id=src.id,
                    source_ref="noenergy",
                    name_en="Mystery stew",
                    name_normalized=normalize_name("Mystery stew"),
                    energy_kcal_per_100g=None,
                ),
            ]
        )
        seeded.commit()
        return seeded

    def test_khong_co_ten_nam_cuoi_cung(self, seeded_messy: Session):
        rows, total = FoodRepository(seeded_messy).search(limit=10)
        assert total == 7
        assert rows[-1].source_ref == "noname"  # không có tên -> cuối cùng
        assert rows[-2].source_ref == "bio"  # tên không đọc được -> sát cuối

    def test_ten_doc_duoc_nhung_thieu_nang_luong_xep_sau_nhom_co_so_lieu(self, seeded_messy: Session):
        rows, _ = FoodRepository(seeded_messy).search(limit=10)
        order = [r.source_ref for r in rows]
        assert order.index("noenergy") == 4  # sau 4 bản ghi có cả tên lẫn năng lượng, trước nhóm rác

    def test_ban_ghi_khong_ten_khong_bi_tim_thay_theo_ten(self, seeded_messy: Session):
        # ẩn khỏi kết quả tìm kiếm theo tên, nhưng vẫn nằm trong danh sách khi không nhập gì
        rows, total = FoodRepository(seeded_messy).search(query="noname")
        assert total == 0 and rows == []

    def test_tu_khoa_ngan_uu_tien_khop_dau_ten(self, db: Session):
        """Tìm 'ga' phải ra 'Ga nuong' trước, không phải 'Grow gain' (chỉ khớp giữa từ)."""
        src = FoodSource(code="rank_src", name="Nguồn xếp hạng", kind="manual")
        db.add(src)
        db.flush()
        for ref, name, kcal in (
            ("mid", "Grow gain shake", 300.0),      # 'ga' nằm trong 'gain' -> khớp giữa
            ("word", "Banh ga ran", 250.0),         # 'ga' là một từ đứng sau
            ("prefix", "Ga nuong", 180.0),          # 'ga' ở đầu tên
        ):
            db.add(Food(source_id=src.id, source_ref=ref, name_en=name,
                        name_normalized=normalize_name(name), cooking_state="cooked",
                        energy_kcal_per_100g=kcal))
        db.commit()

        rows, total = FoodRepository(db).search(query="ga", limit=10)
        assert total == 3
        assert [f.source_ref for f in rows] == ["prefix", "word", "mid"]

    def test_khop_theo_ten_phai_hon_khop_theo_ten_phu(self, db: Session):
        """Bản ghi chỉ khớp nhờ tên phụ (alias) phải xếp SAU bản ghi khớp ở tên chính."""
        src = FoodSource(code="alias_rank", name="Nguồn tên phụ", kind="manual")
        db.add(src)
        db.flush()
        alias_only = Food(source_id=src.id, source_ref="alias_only", name_en="Half Sour Pickle",
                          name_normalized=normalize_name("Half Sour Pickle"), cooking_state="processed",
                          energy_kcal_per_100g=20.0)
        by_name = Food(source_id=src.id, source_ref="by_name", name_en="Ga nuong mat ong",
                       name_normalized=normalize_name("Ga nuong mat ong"), cooking_state="cooked",
                       energy_kcal_per_100g=180.0)
        db.add_all([alias_only, by_name])
        db.flush()
        db.add(FoodAlias(food_id=alias_only.id, alias="ga", alias_normalized=normalize_name("ga")))
        db.commit()

        rows, total = FoodRepository(db).search(query="ga", limit=10)
        assert total == 2
        assert [f.source_ref for f in rows] == ["by_name", "alias_only"]


class TestFtsSearch:
    def test_create_all_tao_bang_fts(self, db: Session):
        table = db.scalar(
            text("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'food_search'")
        )
        assert table == "food_search"

    def test_truy_van_nhieu_tu_dung_and(self, db: Session):
        src = FoodSource(code="fts_and", name="Nguồn FTS", kind="manual")
        db.add(src)
        db.flush()
        db.add(
            Food(
                source_id=src.id,
                source_ref="and",
                name_en="Thit uc ga nuong",
                name_normalized=normalize_name("Thit uc ga nuong"),
                energy_kcal_per_100g=180.0,
            )
        )
        db.commit()

        rows, total = FoodRepository(db).search(query="thịt gà")
        assert total == 1
        assert [row.source_ref for row in rows] == ["and"]

    def test_trigger_food_dong_bo_insert_update_delete(self, db: Session):
        src = FoodSource(code="fts_food", name="Nguồn trigger", kind="manual")
        db.add(src)
        db.flush()
        food = Food(
            source_id=src.id,
            source_ref="trigger",
            name_en="Mon cu",
            name_normalized="mon cu",
        )
        db.add(food)
        db.commit()
        repo = FoodRepository(db)
        assert repo.has_match("mon cu") is True

        food.name_normalized = "mon moi"
        db.commit()
        assert repo.has_match("mon cu") is False
        assert repo.has_match("mon moi") is True

        db.delete(food)
        db.commit()
        assert repo.has_match("mon moi") is False

    def test_trigger_alias_dong_bo_insert_update_delete(self, seeded: Session):
        food = seeded.query(Food).filter(Food.source_ref == "1").one()
        alias = FoodAlias(food_id=food.id, alias="Nước dùng", alias_normalized="nuoc dung")
        seeded.add(alias)
        seeded.commit()
        repo = FoodRepository(seeded)
        assert repo.has_match("nuoc dung") is True

        alias.alias_normalized = "canh bo"
        seeded.commit()
        assert repo.has_match("nuoc dung") is False
        assert repo.has_match("canh bo") is True

        seeded.delete(alias)
        seeded.commit()
        assert repo.has_match("canh bo") is False

    def test_ky_tu_fts_dac_biet_khong_gay_loi(self, seeded: Session):
        rows, total = FoodRepository(seeded).search(query='ga" OR * NEAR (')
        assert rows == []
        assert total == 0

    def test_thieu_bang_fts_tu_ha_cap_ve_like(self, seeded: Session):
        seeded.execute(text("DROP TABLE food_search"))
        seeded.commit()

        rows, total = FoodRepository(seeded).search(query="pho bo")
        assert total == 1
        assert _names(rows) == {"Phở bò"}
