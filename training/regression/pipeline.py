from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

NUMERIC_FEATURES = [
    "protein_g",
    "fat_g",
    "carbohydrate_g",
    "fiber_g",
    "water_g",
    "ash_g",
]
CATEGORICAL_FEATURES = ["food_category", "cooking_state"]
MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET_COLUMN = "energy_kcal_per_100g"

NUTRIENT_NUMBER_TO_COLUMN = {
    203: "protein_g",
    204: "fat_g",
    205: "carbohydrate_g",
    207: "ash_g",
    208: TARGET_COLUMN,
    255: "water_g",
    291: "fiber_g",
}
ATWATER_NUTRIENT_NUMBERS = {957, 958}
ENERGY_KJ_NUTRIENT_NUMBER = 268

_RAW_PATTERN = re.compile(r"\b(raw|uncooked)\b", flags=re.IGNORECASE)
_COOKED_PATTERN = re.compile(
    r"\b(cooked|boiled|baked|broiled|fried|grilled|roasted|steamed|braised|"
    r"stewed|poached|sauteed|microwaved|toasted)\b",
    flags=re.IGNORECASE,
)


def count_resolved_join_keys(
    food_nutrient: pd.DataFrame, nutrient: pd.DataFrame
) -> dict[str, int]:
    """Count unique nutrient keys resolved by each USDA join convention."""
    food_keys = set(
        pd.to_numeric(food_nutrient["nutrient_id"], errors="coerce")
        .dropna()
        .astype(int)
        .unique()
    )
    nutrient_ids = set(
        pd.to_numeric(nutrient["id"], errors="coerce").dropna().astype(int).unique()
    )
    nutrient_numbers = set(
        pd.to_numeric(nutrient["nutrient_nbr"], errors="coerce")
        .dropna()
        .astype(int)
        .unique()
    )
    return {
        "unique_food_nutrient_ids": len(food_keys),
        "resolved_via_nutrient_id": len(food_keys.intersection(nutrient_ids)),
        "resolved_via_nutrient_nbr": len(food_keys.intersection(nutrient_numbers)),
    }


def infer_cooking_state(description: Any) -> str:
    """Infer a coarse cooking state from the USDA food description."""
    text = "" if pd.isna(description) else str(description)
    if _RAW_PATTERN.search(text):
        return "raw"
    if _COOKED_PATTERN.search(text):
        return "cooked"
    return "unspecified_or_processed"


def normalize_description(description: Any) -> str:
    """Normalize a description for leakage-safe grouping."""
    text = "" if pd.isna(description) else str(description).lower()
    normalized = re.sub(r"[^a-z0-9]+", "", text)
    return normalized or "missing-description"


def assemble_source_features(
    food: pd.DataFrame,
    food_nutrient: pd.DataFrame,
    nutrient: pd.DataFrame,
    categories: pd.DataFrame,
    *,
    source: str,
    required_data_type: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any], pd.Series]:
    """Create one source's leakage-controlled feature rows and audit counts."""
    candidates = food.copy()
    if required_data_type is not None:
        candidates = candidates[candidates["data_type"].eq(required_data_type)].copy()
    candidates = candidates.drop_duplicates(subset=["fdc_id"], keep="first")

    nutrient_lookup = nutrient[["id", "nutrient_nbr", "name", "unit_name"]].copy()
    joined = food_nutrient.merge(
        nutrient_lookup,
        left_on="nutrient_id",
        right_on="id",
        how="left",
        validate="many_to_one",
    )
    joined = joined[joined["fdc_id"].isin(candidates["fdc_id"])].copy()
    joined["nutrient_nbr"] = pd.to_numeric(joined["nutrient_nbr"], errors="coerce")
    joined["amount"] = pd.to_numeric(joined["amount"], errors="coerce")

    measured = joined[joined["nutrient_nbr"].eq(208)]
    atwater = joined[joined["nutrient_nbr"].isin(ATWATER_NUTRIENT_NUMBERS)]
    measured_foods = set(measured.loc[measured["amount"].notna(), "fdc_id"])
    atwater_foods = set(atwater.loc[atwater["amount"].notna(), "fdc_id"])

    selected = joined[
        joined["nutrient_nbr"].isin(NUTRIENT_NUMBER_TO_COLUMN)
    ].copy()
    relevant_duplicate_rows = int(
        selected.duplicated(subset=["fdc_id", "nutrient_nbr"], keep=False).sum()
    )
    pivot = selected.pivot_table(
        index="fdc_id", columns="nutrient_nbr", values="amount", aggfunc="mean"
    ).rename(columns=NUTRIENT_NUMBER_TO_COLUMN)
    for column in NUTRIENT_NUMBER_TO_COLUMN.values():
        if column not in pivot.columns:
            pivot[column] = np.nan

    category_lookup = categories[["id", "description"]].drop_duplicates("id").rename(
        columns={"id": "food_category_id", "description": "food_category"}
    )
    assembled = candidates.merge(category_lookup, on="food_category_id", how="left")
    assembled = assembled.merge(
        pivot[list(NUTRIENT_NUMBER_TO_COLUMN.values())],
        left_on="fdc_id",
        right_index=True,
        how="left",
    )
    unknown_category_count = int(assembled["food_category"].isna().sum())
    assembled["food_category"] = assembled["food_category"].fillna("Unknown")
    assembled["cooking_state"] = assembled["description"].map(infer_cooking_state)
    assembled["source"] = source

    target_missing = assembled[TARGET_COLUMN].isna()
    output = assembled.loc[
        ~target_missing, ["fdc_id", "source"] + MODEL_FEATURES + [TARGET_COLUMN]
    ].copy()
    descriptions = assembled.loc[~target_missing, "description"].reset_index(drop=True)
    output = output.reset_index(drop=True)

    audit: dict[str, Any] = {
        "source": source,
        "candidate_food_rows": int(len(candidates)),
        "measured_target_rows_retained": int(len(output)),
        "missing_measured_target_rows_removed": int(target_missing.sum()),
        "atwater_nutrient_rows_excluded": int(len(atwater)),
        "atwater_unique_foods": int(len(atwater_foods)),
        "atwater_only_foods_excluded": int(len(atwater_foods - measured_foods)),
        "foods_with_measured_and_atwater_energy": int(
            len(atwater_foods.intersection(measured_foods))
        ),
        "energy_kj_nutrient_rows_excluded": int(
            joined["nutrient_nbr"].eq(ENERGY_KJ_NUTRIENT_NUMBER).sum()
        ),
        "duplicate_relevant_nutrient_rows": relevant_duplicate_rows,
        "unknown_food_category_rows_filled": unknown_category_count,
        "missing_features_before_imputation": {
            column: int(output[column].isna().sum()) for column in MODEL_FEATURES
        },
    }
    return output, audit, descriptions


def split_by_description_group(
    descriptions: pd.Series, *, random_state: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Split 70/15/15 while keeping normalized descriptions in one partition."""
    groups = descriptions.map(normalize_description).to_numpy()
    positions = np.arange(len(descriptions))
    first_split = GroupShuffleSplit(
        n_splits=1, test_size=0.30, random_state=random_state
    )
    train_idx, holdout_idx = next(first_split.split(positions, groups=groups))

    holdout_groups = groups[holdout_idx]
    second_split = GroupShuffleSplit(
        n_splits=1, test_size=0.50, random_state=random_state + 1
    )
    validation_rel, test_rel = next(
        second_split.split(holdout_idx, groups=holdout_groups)
    )
    validation_idx = holdout_idx[validation_rel]
    test_idx = holdout_idx[test_rel]
    return train_idx, validation_idx, test_idx

