from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

REGRESSION_DIR = Path(__file__).resolve().parents[1]
if str(REGRESSION_DIR) not in sys.path:
    sys.path.insert(0, str(REGRESSION_DIR))

from pipeline import (
    MODEL_FEATURES,
    assemble_source_features,
    count_resolved_join_keys,
    infer_cooking_state,
    split_by_description_group,
)


class JoinKeyAuditTests(unittest.TestCase):
    def test_counts_resolution_against_id_and_nutrient_number(self) -> None:
        food_nutrient = pd.DataFrame({"nutrient_id": [1003, 1003, 208, 9999]})
        nutrient = pd.DataFrame(
            {
                "id": [1003, 1008],
                "nutrient_nbr": [203, 208],
            }
        )

        result = count_resolved_join_keys(food_nutrient, nutrient)

        self.assertEqual(
            result,
            {
                "unique_food_nutrient_ids": 3,
                "resolved_via_nutrient_id": 1,
                "resolved_via_nutrient_nbr": 1,
            },
        )


class FeatureAssemblyTests(unittest.TestCase):
    def test_uses_only_measured_energy_and_audits_atwater_exclusion(self) -> None:
        food = pd.DataFrame(
            {
                "fdc_id": [1, 2, 3],
                "data_type": ["foundation_food"] * 3,
                "description": ["Apple, raw", "Bread, baked", "Unknown food"],
                "food_category_id": [10, 20, pd.NA],
            }
        )
        nutrient = pd.DataFrame(
            {
                "id": [1003, 1004, 1005, 1007, 1008, 1051, 1079, 2047, 2048],
                "nutrient_nbr": [203, 204, 205, 207, 208, 255, 291, 957, 958],
                "name": ["Protein", "Fat", "Carbohydrate", "Ash", "Energy", "Water", "Fiber", "Atwater general", "Atwater specific"],
                "unit_name": ["G", "G", "G", "G", "KCAL", "G", "G", "KCAL", "KCAL"],
            }
        )
        records = []
        for fdc_id in [1, 2]:
            for nutrient_id, amount in [(1003, 1), (1004, 2), (1005, 3), (1007, 4), (1051, 80), (1079, 5)]:
                records.append({"fdc_id": fdc_id, "nutrient_id": nutrient_id, "amount": amount})
        records.extend(
            [
                {"fdc_id": 1, "nutrient_id": 1008, "amount": 123},
                {"fdc_id": 1, "nutrient_id": 2047, "amount": 999},
                {"fdc_id": 2, "nutrient_id": 2048, "amount": 777},
            ]
        )
        food_nutrient = pd.DataFrame(records)
        categories = pd.DataFrame(
            {"id": [10, 20], "description": ["Fruit", "Baked products"]}
        )

        matrix, audit, descriptions = assemble_source_features(
            food,
            food_nutrient,
            nutrient,
            categories,
            source="Foundation",
            required_data_type="foundation_food",
        )

        self.assertEqual(matrix["fdc_id"].tolist(), [1])
        self.assertEqual(matrix["energy_kcal_per_100g"].tolist(), [123])
        self.assertEqual(audit["atwater_nutrient_rows_excluded"], 2)
        self.assertEqual(audit["atwater_only_foods_excluded"], 1)
        self.assertEqual(audit["missing_measured_target_rows_removed"], 2)
        self.assertEqual(descriptions.tolist(), ["Apple, raw"])

    def test_model_features_exclude_identifiers_source_and_all_energy(self) -> None:
        self.assertEqual(
            MODEL_FEATURES,
            [
                "protein_g",
                "fat_g",
                "carbohydrate_g",
                "fiber_g",
                "water_g",
                "ash_g",
                "food_category",
                "cooking_state",
            ],
        )
        self.assertFalse(any("energy" in name for name in MODEL_FEATURES))


class CookingStateTests(unittest.TestCase):
    def test_classifies_raw_cooked_and_unspecified_descriptions(self) -> None:
        self.assertEqual(infer_cooking_state("Carrots, raw"), "raw")
        self.assertEqual(infer_cooking_state("Beef, cooked, braised"), "cooked")
        self.assertEqual(infer_cooking_state("Milk, whole"), "unspecified_or_processed")


class SplitTests(unittest.TestCase):
    def test_description_groups_never_cross_splits(self) -> None:
        descriptions = pd.Series(
            ["Apple, raw", "Apple raw", "Bread", "Soup", "Stew", "Rice", "Beans", "Fish", "Egg", "Milk"]
        )
        train_idx, validation_idx, test_idx = split_by_description_group(
            descriptions, random_state=42
        )
        normalized = descriptions.str.lower().str.replace(r"[^a-z0-9]+", "", regex=True)
        groups = {
            split: set(normalized.iloc[index])
            for split, index in {
                "train": train_idx,
                "validation": validation_idx,
                "test": test_idx,
            }.items()
        }
        self.assertTrue(groups["train"].isdisjoint(groups["validation"]))
        self.assertTrue(groups["train"].isdisjoint(groups["test"]))
        self.assertTrue(groups["validation"].isdisjoint(groups["test"]))
        self.assertEqual(
            sorted(train_idx.tolist() + validation_idx.tolist() + test_idx.tolist()),
            list(range(len(descriptions))),
        )


if __name__ == "__main__":
    unittest.main()
