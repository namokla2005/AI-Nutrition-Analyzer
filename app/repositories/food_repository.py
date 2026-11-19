"""Truy vấn thực phẩm: tìm theo tiếng Việt (có dấu và không dấu), lọc theo nhóm/trạng thái."""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.utils import normalize_name
from app.models import Food, FoodAlias, FoodNutrient, Nutrient

ENERGY_CODE = "energy_kcal"


class FoodRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- truy vấn ----------

    def get(self, food_id: int) -> Food | None:
        return self.db.get(Food, food_id)

    def get_with_nutrients(self, food_id: int) -> Food | None:
        stmt = (
            select(Food)
            .options(selectinload(Food.nutrients).selectinload(FoodNutrient.nutrient))
            .where(Food.id == food_id)
        )
        return self.db.scalars(stmt).first()

    def _apply_filters(
        self,
        stmt: Select,
        query: str | None,
        category: str | None,
        cooking_state: str | None,
        food_group: str | None,
        min_kcal: float | None,
        max_kcal: float | None,
    ) -> Select:
        if query:
            like = f"%{normalize_name(query)}%"
            sub = select(FoodAlias.food_id).where(FoodAlias.alias_normalized.like(like))
            stmt = stmt.where(
                or_(
                    Food.name_normalized.like(like),
                    Food.id.in_(sub),
                )
            )
        if category:
            stmt = stmt.where(Food.category == category)
        if cooking_state:
            stmt = stmt.where(Food.cooking_state == cooking_state)
        if food_group:
            stmt = stmt.where(Food.food_group == food_group)
        if min_kcal is not None:
            stmt = stmt.where(Food.energy_kcal_per_100g >= min_kcal)
        if max_kcal is not None:
            stmt = stmt.where(Food.energy_kcal_per_100g <= max_kcal)
        return stmt

    def search(
        self,
        query: str | None = None,
        category: str | None = None,
        cooking_state: str | None = None,
        food_group: str | None = None,
        min_kcal: float | None = None,
        max_kcal: float | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Food], int]:
        """Trả về (danh sách thực phẩm, tổng số bản ghi khớp)."""
        limit = max(1, min(int(limit), 100))
        base = self._apply_filters(
            select(Food), query, category, cooking_state, food_group, min_kcal, max_kcal
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = int(self.db.scalar(count_stmt) or 0)
        # Xếp hạng kết quả cho dễ dùng với dữ liệu thật nhiều nguồn:
        #  - Open Food Facts có tên tiếng Bulgaria/Nga/Thái... ; `normalize_name` bỏ ký tự
        #    không phải Latin nên chúng thành chuỗi rỗng hoặc chỉ còn chữ số và chen lên đầu.
        #  - 759 bản ghi không có tên nào cả (hiển thị "Chưa có tên") phải nằm cuối cùng.
        #  - Bản ghi đã có số liệu năng lượng hữu ích hơn bản ghi thiếu số liệu.
        # GLOB là cú pháp của SQLite — dự án chỉ dùng SQLite (quyết định TD-01).
        has_name = (func.coalesce(func.trim(Food.name_en), "") != "") | (
            func.coalesce(func.trim(Food.name_vi), "") != ""
        )
        unreadable = (Food.name_normalized == "") | Food.name_normalized.op("GLOB")("[0-9]*")
        rank = case((~has_name, 2), (unreadable, 1), else_=0)
        # Độ liên quan khi có từ khoá: tìm "gà" mà để "Grow & gain" lên đầu (khớp giữa từ)
        # là vô dụng. Ưu tiên: khớp đúng cả tên > khớp đầu tên > khớp đầu một từ > khớp giữa.
        order_by: list = [rank.asc()]
        normalized_query = normalize_name(query) if query else ""
        if normalized_query:
            relevance = case(
                (Food.name_normalized == normalized_query, 0),
                (Food.name_normalized.like(f"{normalized_query}%"), 1),
                (Food.name_normalized.like(f"% {normalized_query}%"), 2),
                # khớp đâu đó trong tên vẫn hơn khớp chỉ nhờ tên phụ (alias)
                (Food.name_normalized.like(f"%{normalized_query}%"), 3),
                else_=4,
            )
            order_by.insert(0, relevance.asc())
        order_by += [
            Food.energy_kcal_per_100g.is_(None).asc(),
            Food.name_normalized.asc(),
            Food.id.asc(),
        ]
        rows = list(
            self.db.scalars(
                base.order_by(*order_by)
                .limit(limit)
                .offset(max(0, offset))
            )
        )
        return rows, total

    def nutrient_values_per_100g(self, food_id: int) -> dict[str, float | None]:
        """Lấy giá trị/100 g theo mã chất. Chất thiếu sẽ KHÔNG xuất hiện với giá trị 0."""
        stmt = (
            select(Nutrient.code, FoodNutrient.amount_per_100g)
            .join(FoodNutrient, FoodNutrient.nutrient_id == Nutrient.id)
            .where(FoodNutrient.food_id == food_id)
        )
        return {code: amount for code, amount in self.db.execute(stmt)}

    def distinct_categories(self) -> list[str]:
        rows = self.db.execute(
            select(Food.category).where(Food.category.is_not(None)).distinct().order_by(Food.category)
        )
        return [r[0] for r in rows if r[0]]

    def distinct_food_groups(self) -> list[str]:
        rows = self.db.execute(
            select(Food.food_group).where(Food.food_group.is_not(None)).distinct().order_by(Food.food_group)
        )
        return [r[0] for r in rows if r[0]]

    def count_by_source(self) -> list[tuple[str, int]]:
        from app.models import FoodSource

        stmt = (
            select(FoodSource.code, func.count(Food.id))
            .join(Food, Food.source_id == FoodSource.id)
            .group_by(FoodSource.code)
            .order_by(FoodSource.code)
        )
        return [(code, int(n)) for code, n in self.db.execute(stmt)]

    # ---------- ghi dữ liệu ----------

    def find_by_source_ref(self, source_id: int, source_ref: str) -> Food | None:
        stmt = select(Food).where(Food.source_id == source_id, Food.source_ref == source_ref)
        return self.db.scalars(stmt).first()

    def upsert_nutrient(
        self, food_id: int, nutrient_id: int, amount: float | None, unit: str, quality: str | None = None
    ) -> None:
        stmt = select(FoodNutrient).where(
            FoodNutrient.food_id == food_id, FoodNutrient.nutrient_id == nutrient_id
        )
        row = self.db.scalars(stmt).first()
        if row is None:
            row = FoodNutrient(
                food_id=food_id,
                nutrient_id=nutrient_id,
                amount_per_100g=amount,
                unit=unit,
                data_quality=quality,
            )
            self.db.add(row)
        else:
            row.amount_per_100g = amount
            row.unit = unit
            row.data_quality = quality
        # giữ tính nhất quán khi session đặt autoflush=False
        self.db.flush()

    def sync_energy_cache(self, food_id: int) -> float | None:
        """Đồng bộ `foods.energy_kcal_per_100g` từ bảng food_nutrients (nguồn chuẩn - TD-04)."""
        stmt = (
            select(FoodNutrient.amount_per_100g)
            .join(Nutrient, Nutrient.id == FoodNutrient.nutrient_id)
            .where(FoodNutrient.food_id == food_id, Nutrient.code == ENERGY_CODE)
        )
        value = self.db.scalar(stmt)
        food = self.db.get(Food, food_id)
        if food is not None:
            food.energy_kcal_per_100g = value
        return value

    def add_alias(self, food_id: int, alias: str, lang: str = "vi") -> None:
        norm = normalize_name(alias)
        if not norm:
            return
        exists = self.db.scalars(
            select(FoodAlias).where(FoodAlias.food_id == food_id, FoodAlias.alias_normalized == norm)
        ).first()
        if exists is None:
            self.db.add(FoodAlias(food_id=food_id, alias=alias, alias_normalized=norm, lang=lang))
            # Session được tạo với autoflush=False, nên phải flush để lần gọi sau
            # nhìn thấy bản ghi này (nếu không sẽ tạo alias trùng).
            self.db.flush()

    def aliases(self, food_id: int) -> Sequence[FoodAlias]:
        return list(self.db.scalars(select(FoodAlias).where(FoodAlias.food_id == food_id)))
