from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from pipeline import (
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
    assemble_source_features,
    count_resolved_join_keys,
    normalize_description,
    split_by_description_group,
)

RANDOM_STATE = 42

DATASETS = {
    "SR Legacy": "FoodData_Central_sr_legacy_food_csv_2018-04",
    "Foundation": "FoodData_Central_foundation_food_csv_2024-10-31",
    "Survey/FNDDS": "FoodData_Central_survey_food_csv_2022-10-28",
}


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False, **kwargs)


def load_model_source(dataset_dir: Path) -> dict[str, pd.DataFrame]:
    return {
        "food": read_csv(
            dataset_dir / "food.csv",
            usecols=["fdc_id", "data_type", "description", "food_category_id"],
        ),
        "food_nutrient": read_csv(
            dataset_dir / "food_nutrient.csv",
            usecols=["fdc_id", "nutrient_id", "amount"],
        ),
        "nutrient": read_csv(
            dataset_dir / "nutrient.csv",
            usecols=["id", "name", "unit_name", "nutrient_nbr"],
        ),
        "category": read_csv(
            dataset_dir / "food_category.csv", usecols=["id", "description"]
        ),
    }


def validate_measured_energy_definition(nutrient: pd.DataFrame, source: str) -> None:
    numbers = pd.to_numeric(nutrient["nutrient_nbr"], errors="coerce")
    definition = nutrient.loc[numbers.eq(208), ["name", "unit_name"]]
    if len(definition) != 1:
        raise ValueError(f"{source}: nutrient_nbr 208 must have exactly one definition")
    row = definition.iloc[0]
    if row["name"] != "Energy" or str(row["unit_name"]).upper() != "KCAL":
        raise ValueError(f"{source}: nutrient_nbr 208 is not measured Energy [KCAL]")


def make_preprocessor() -> ColumnTransformer:
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def build_models() -> dict[str, tuple[str, Any, dict[str, Any]]]:
    return {
        "baseline_mean": (
            "DummyRegressor",
            DummyRegressor(strategy="mean"),
            {"strategy": "mean"},
        ),
        "linear_regression": (
            "LinearRegression",
            LinearRegression(),
            {"fit_intercept": True},
        ),
        "random_forest": (
            "RandomForestRegressor",
            RandomForestRegressor(
                n_estimators=250,
                min_samples_leaf=2,
                max_features=1.0,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
            {
                "n_estimators": 250,
                "min_samples_leaf": 2,
                "max_features": 1.0,
                "max_depth": None,
                "random_state": RANDOM_STATE,
                "n_jobs": -1,
            },
        ),
        "gradient_boosting": (
            "GradientBoostingRegressor",
            GradientBoostingRegressor(
                n_estimators=250,
                learning_rate=0.05,
                max_depth=3,
                min_samples_leaf=3,
                subsample=0.9,
                random_state=RANDOM_STATE,
            ),
            {
                "n_estimators": 250,
                "learning_rate": 0.05,
                "max_depth": 3,
                "min_samples_leaf": 3,
                "subsample": 0.9,
                "random_state": RANDOM_STATE,
                "loss": "squared_error",
            },
        ),
    }


def regression_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(root_mean_squared_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def markdown_metrics(metrics: dict[str, Any]) -> str:
    labels = {
        "baseline_mean": "Baseline (trung bình tập train)",
        "linear_regression": "Linear Regression",
        "random_forest": "Random Forest Regressor",
        "gradient_boosting": "Gradient Boosting Regressor",
    }
    split_labels = {"train": "Train", "validation": "Validation", "test": "Test"}
    lines = [
        "| Mô hình | Tập | MAE (kcal/100 g) | RMSE (kcal/100 g) | R² |",
        "|---|---:|---:|---:|---:|",
    ]
    for model_key in labels:
        for split in ["train", "validation", "test"]:
            values = metrics[model_key][split]
            lines.append(
                f"| {labels[model_key]} | {split_labels[split]} | "
                f"{values['mae']:.4f} | {values['rmse']:.4f} | {values['r2']:.4f} |"
            )
    return "\n".join(lines)


def create_report(
    *,
    command: str,
    generated_at: str,
    join_audit: dict[str, Any],
    source_audits: list[dict[str, Any]],
    feature_matrix: pd.DataFrame,
    split_sizes: dict[str, int],
    split_group_counts: dict[str, int],
    missing_totals: dict[str, int],
    imputer_medians: dict[str, float],
    metrics: dict[str, Any],
    fit_seconds: dict[str, float],
    best_model: str,
    figure_relative_path: str,
    versions: dict[str, str],
) -> str:
    source_rows = []
    for audit in source_audits:
        source_rows.append(
            f"| {audit['source']} | {audit['candidate_food_rows']} | "
            f"{audit['measured_target_rows_retained']} | "
            f"{audit['missing_measured_target_rows_removed']} | "
            f"{audit['atwater_nutrient_rows_excluded']} | "
            f"{audit['atwater_only_foods_excluded']} | "
            f"{audit['energy_kj_nutrient_rows_excluded']} |"
        )
    join_rows = []
    for source, audit in join_audit.items():
        join_rows.append(
            f"| {source} | {audit['unique_food_nutrient_ids']} | "
            f"{audit['resolved_via_nutrient_id']} | "
            f"{audit['resolved_via_nutrient_nbr']} |"
        )
    missing_rows = []
    for feature in MODEL_FEATURES:
        count = missing_totals.get(feature, 0)
        action = "median học từ train" if feature in imputer_medians and count else "không cần"
        detail = f" (median={imputer_medians[feature]:.4f})" if count else ""
        missing_rows.append(f"| {feature} | {count} | {action}{detail} |")

    baseline_test = metrics["baseline_mean"]["test"]
    winner_test = metrics[best_model]["test"]
    rmse_gain = 100.0 * (baseline_test["rmse"] - winner_test["rmse"]) / baseline_test[
        "rmse"
    ]
    mae_gain = 100.0 * (baseline_test["mae"] - winner_test["mae"]) / baseline_test[
        "mae"
    ]
    useful = winner_test["r2"] > 0 and rmse_gain > 0
    winner_label = {
        "linear_regression": "Linear Regression",
        "random_forest": "Random Forest Regressor",
        "gradient_boosting": "Gradient Boosting Regressor",
    }[best_model]
    conclusion = (
        "có ích so với baseline" if useful else "chưa chứng minh được lợi ích so với baseline"
    )

    return f"""# Thí nghiệm hồi quy năng lượng USDA FoodData Central

- Thời điểm chạy (UTC): `{generated_at}`
- Lệnh tái lập: `{command}`
- `random_state=42` cho tách train/holdout và mô hình; lần tách validation/test dùng `random_state=43`.
- Đơn vị đích: **kcal trên 100 g**.

## 1. Kiểm tra khóa nối USDA

Đếm trên **các `nutrient_id` duy nhất** của từng `food_nutrient.csv`:

| Nguồn | Số ID duy nhất | Khớp `nutrient.id` | Khớp `nutrient.nutrient_nbr` |
|---|---:|---:|---:|
{chr(10).join(join_rows)}

Kết quả xác nhận SR Legacy và Foundation phải nối `food_nutrient.nutrient_id -> nutrient.id`; Survey/FNDDS phải nối vào `nutrient.nutrient_nbr`. Survey chỉ được dùng để kiểm tra khóa, không đi vào ma trận huấn luyện.

## 2. Dữ liệu, đích và quy tắc loại dòng

| Nguồn | Dòng thực phẩm ứng viên | Giữ lại có Energy 208 | Loại vì thiếu đích 208 | Bản ghi Atwater 957/958 bị loại | Thực phẩm chỉ có Atwater | Bản ghi Energy kJ 268 bị loại khỏi feature |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(source_rows)}

Tổng ma trận cuối: **{len(feature_matrix)} dòng** ({feature_matrix['source'].value_counts().to_dict()}). Không nội suy đích. Foundation chỉ lấy `data_type=foundation_food`; SR Legacy lấy `data_type=sr_legacy_food`.

## 3. Kiểm soát rò rỉ đặc trưng

1. Đích chỉ là nutrient `nutrient_nbr=208`, tên `Energy`, đơn vị `KCAL`. Các giá trị Atwater 957/958 không bao giờ được chọn làm đích. Có **{sum(a['atwater_nutrient_rows_excluded'] for a in source_audits)} bản ghi nutrient Atwater** bị loại; **{sum(a['atwater_only_foods_excluded'] for a in source_audits)} thực phẩm chỉ có Atwater** không được đưa vào ma trận. Các thực phẩm vừa có 208 vừa có Atwater vẫn được giữ nhưng chỉ dùng 208.
2. Energy kJ (`nutrient_nbr=268`) bị loại hoàn toàn; không có cột năng lượng hay cột suy ra từ năng lượng trong feature.
3. `fdc_id`, `source`, mô tả gốc và đích không phải feature. Danh sách feature chính xác: `{MODEL_FEATURES}`.
4. Tách dữ liệu theo **nhóm mô tả chuẩn hóa** trước khi fit. Một mô tả chuẩn hóa không thể xuất hiện ở nhiều tập. Số nhóm: {split_group_counts}. Giao giữa mọi cặp tập đã kiểm tra bằng 0.
5. Median và one-hot encoder chỉ `fit` trên train trong `Pipeline`; validation/test chỉ được `transform`. Chọn mô hình thắng bằng RMSE validation, không dùng test để chọn.

`cooking_state` được suy ra tất định từ từ khóa mô tả: `raw/uncooked` → `raw`; các từ khóa cooked/boiled/baked/broiled/fried/grilled/roasted/steamed/braised/stewed/poached/sauteed/microwaved/toasted → `cooked`; còn lại → `unspecified_or_processed`.

## 4. Thiếu dữ liệu

| Feature | Số giá trị thiếu trước split | Xử lý |
|---|---:|---|
{chr(10).join(missing_rows)}

Không loại dòng vì thiếu feature. Chỉ các feature thực sự có thiếu mới bị tác động bởi median; lý do: thiếu bản ghi dinh dưỡng không đồng nghĩa giá trị bằng 0, và median train bền vững hơn mean trước ngoại lệ. Category thiếu được gán nhãn `Unknown`; `cooking_state` luôn có nhãn. Target thiếu bị loại, tuyệt đối không nội suy.

## 5. Chia dữ liệu

- Train: **{split_sizes['train']}** dòng
- Validation: **{split_sizes['validation']}** dòng
- Test: **{split_sizes['test']}** dòng

Tỷ lệ đích xấp xỉ 70/15/15; chênh lệch nhỏ có thể xuất hiện do ràng buộc nhóm mô tả.

## 6. Mô hình và kết quả thực chạy

- Baseline: dự đoán trung bình target của train.
- Linear Regression: `fit_intercept=True`.
- Random Forest: 250 cây, `min_samples_leaf=2`, `max_features=1.0`, `n_jobs=-1`, `random_state=42`.
- Gradient Boosting: 250 cây, `learning_rate=0.05`, `max_depth=3`, `min_samples_leaf=3`, `subsample=0.9`, `random_state=42`.

{markdown_metrics(metrics)}

Thời gian fit (giây): `{json.dumps(fit_seconds, ensure_ascii=False)}`.

## 7. Diễn giải

Mô hình thắng theo RMSE validation là **{winner_label}**. Trên test, mô hình này đạt MAE **{winner_test['mae']:.4f}**, RMSE **{winner_test['rmse']:.4f}**, R² **{winner_test['r2']:.4f}**. So với baseline test, MAE cải thiện **{mae_gain:.2f}%** và RMSE cải thiện **{rmse_gain:.2f}%**; theo tiêu chí R² dương và RMSE tốt hơn baseline, mô hình **{conclusion}**. Đây là đánh giá nội bộ theo FoodData Central, chưa phải kiểm định ngoài miền dữ liệu.

![Dự đoán so với thực tế]({figure_relative_path})

## 8. Phiên bản thư viện

`{json.dumps(versions, ensure_ascii=False)}`
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run USDA calorie regression experiment")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    usda_root = project_root / "data" / "external" / "usda"
    processed_dir = project_root / "data" / "processed"
    model_dir = project_root / "models" / "regression"
    report_dir = project_root / "data" / "reports"
    figure_dir = report_dir / "figures"
    for directory in [processed_dir, model_dir, report_dir, figure_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    loaded = {
        source: load_model_source(usda_root / DATASETS[source])
        for source in ["SR Legacy", "Foundation"]
    }

    join_audit: dict[str, Any] = {}
    for source in ["SR Legacy", "Foundation"]:
        frames = loaded[source]
        join_audit[source] = count_resolved_join_keys(
            frames["food_nutrient"], frames["nutrient"]
        )
        validate_measured_energy_definition(frames["nutrient"], source)
    survey_dir = usda_root / DATASETS["Survey/FNDDS"]
    survey_fn = read_csv(survey_dir / "food_nutrient.csv", usecols=["nutrient_id"])
    survey_nutrient = read_csv(
        survey_dir / "nutrient.csv", usecols=["id", "nutrient_nbr"]
    )
    join_audit["Survey/FNDDS"] = count_resolved_join_keys(
        survey_fn, survey_nutrient
    )
    print("JOIN_KEY_AUDIT=" + json.dumps(join_audit, ensure_ascii=False))

    sr_matrix, sr_audit, sr_descriptions = assemble_source_features(
        loaded["SR Legacy"]["food"],
        loaded["SR Legacy"]["food_nutrient"],
        loaded["SR Legacy"]["nutrient"],
        loaded["SR Legacy"]["category"],
        source="SR Legacy",
        required_data_type="sr_legacy_food",
    )
    foundation_matrix, foundation_audit, foundation_descriptions = (
        assemble_source_features(
            loaded["Foundation"]["food"],
            loaded["Foundation"]["food_nutrient"],
            loaded["Foundation"]["nutrient"],
            loaded["Foundation"]["category"],
            source="Foundation",
            required_data_type="foundation_food",
        )
    )
    source_audits = [sr_audit, foundation_audit]
    print("SOURCE_AUDIT=" + json.dumps(source_audits, ensure_ascii=False))

    matrix = pd.concat([sr_matrix, foundation_matrix], ignore_index=True)
    descriptions = pd.concat(
        [sr_descriptions, foundation_descriptions], ignore_index=True
    )
    if matrix["fdc_id"].duplicated().any():
        raise ValueError("fdc_id is not unique in the final feature matrix")
    if len(matrix) != len(descriptions):
        raise ValueError("description groups are not aligned with feature rows")
    forbidden = {"fdc_id", "source", TARGET_COLUMN}
    if forbidden.intersection(MODEL_FEATURES) or any(
        token in feature.lower()
        for feature in MODEL_FEATURES
        for token in ["energy", "kcal", "kilojoule", "kj"]
    ):
        raise ValueError("Leakage feature detected")

    feature_path = processed_dir / "regression_features.csv"
    matrix.to_csv(feature_path, index=False, encoding="utf-8")

    train_idx, validation_idx, test_idx = split_by_description_group(
        descriptions, random_state=RANDOM_STATE
    )
    split_indices = {
        "train": train_idx,
        "validation": validation_idx,
        "test": test_idx,
    }
    normalized_groups = descriptions.map(normalize_description)
    group_sets = {
        split: set(normalized_groups.iloc[index])
        for split, index in split_indices.items()
    }
    if not (
        group_sets["train"].isdisjoint(group_sets["validation"])
        and group_sets["train"].isdisjoint(group_sets["test"])
        and group_sets["validation"].isdisjoint(group_sets["test"])
    ):
        raise ValueError("Description group leakage across splits")

    assignments = []
    for split, index in split_indices.items():
        part = matrix.iloc[index][["fdc_id", "source"]].copy()
        part["split"] = split
        assignments.append(part)
    split_assignment = pd.concat(assignments, ignore_index=True).sort_values("fdc_id")
    split_path = processed_dir / "regression_split_assignments.csv"
    split_assignment.to_csv(split_path, index=False, encoding="utf-8")

    X = matrix[MODEL_FEATURES]
    y = matrix[TARGET_COLUMN]
    data_partitions = {
        split: (X.iloc[index], y.iloc[index]) for split, index in split_indices.items()
    }
    X_train, y_train = data_partitions["train"]

    models = build_models()
    fitted: dict[str, Pipeline] = {}
    metrics: dict[str, Any] = {}
    fit_seconds: dict[str, float] = {}
    model_specs: dict[str, Any] = {}
    for key, (algorithm, estimator, hyperparameters) in models.items():
        model = Pipeline(
            [("preprocessor", make_preprocessor()), ("regressor", estimator)]
        )
        started = time.perf_counter()
        model.fit(X_train, y_train)
        fit_seconds[key] = round(time.perf_counter() - started, 4)
        fitted[key] = model
        metrics[key] = {}
        for split, (X_split, y_split) in data_partitions.items():
            predictions = model.predict(X_split)
            metrics[key][split] = regression_metrics(y_split, predictions)
        model_specs[key] = {
            "algorithm": algorithm,
            "hyperparameters": hyperparameters,
        }
        print(
            f"MODEL_RESULT {key} fit_seconds={fit_seconds[key]} "
            + json.dumps(metrics[key], ensure_ascii=False)
        )

    candidates = ["linear_regression", "random_forest", "gradient_boosting"]
    best_model = min(candidates, key=lambda key: metrics[key]["validation"]["rmse"])
    best_predictions = fitted[best_model].predict(data_partitions["test"][0])
    y_test = data_partitions["test"][1]
    lower = float(min(y_test.min(), best_predictions.min()))
    upper = float(max(y_test.max(), best_predictions.max()))
    figure_path = figure_dir / f"{best_model}_predicted_vs_actual.png"
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.scatter(y_test, best_predictions, alpha=0.55, s=24, edgecolors="none")
    ax.plot([lower, upper], [lower, upper], "r--", linewidth=1.5, label="Dự đoán hoàn hảo")
    ax.set_xlabel("Năng lượng thực tế (kcal/100 g)")
    ax.set_ylabel("Năng lượng dự đoán (kcal/100 g)")
    ax.set_title(f"Dự đoán so với thực tế — {best_model}")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(figure_path, dpi=180)
    plt.close(fig)

    first_preprocessor = fitted["linear_regression"].named_steps["preprocessor"]
    numeric_imputer = first_preprocessor.named_transformers_["numeric"].named_steps[
        "imputer"
    ]
    imputer_medians = {
        feature: float(value)
        for feature, value in zip(NUMERIC_FEATURES, numeric_imputer.statistics_)
    }
    missing_totals = {
        feature: int(matrix[feature].isna().sum()) for feature in MODEL_FEATURES
    }
    actually_imputed = {
        feature: imputer_medians[feature]
        for feature in NUMERIC_FEATURES
        if missing_totals[feature] > 0
    }

    generated_at = datetime.now(timezone.utc).isoformat()
    versions = {
        "python": platform.python_version(),
        "scikit-learn": sklearn.__version__,
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "joblib": joblib.__version__,
        "matplotlib": matplotlib.__version__,
    }
    split_sizes = {split: int(len(index)) for split, index in split_indices.items()}
    split_group_counts = {
        split: int(len(groups)) for split, groups in group_sets.items()
    }
    provenance = {
        "sources": {
            "SR Legacy": f"data/external/usda/{DATASETS['SR Legacy']}",
            "Foundation": f"data/external/usda/{DATASETS['Foundation']}",
            "Survey/FNDDS (join audit only)": f"data/external/usda/{DATASETS['Survey/FNDDS']}",
        },
        "source_counts": matrix["source"].value_counts().to_dict(),
        "source_audits": source_audits,
        "join_key_audit": join_audit,
    }
    common_metadata = {
        "created_at_utc": generated_at,
        "target": TARGET_COLUMN,
        "target_units": "kcal per 100 g",
        "feature_units": {
            **{feature: "g per 100 g" for feature in NUMERIC_FEATURES},
            "food_category": "categorical",
            "cooking_state": "categorical",
        },
        "feature_list": MODEL_FEATURES,
        "provenance": provenance,
        "missing_value_rules": {
            "target": "drop; never impute",
            "numeric_features": "training-set median via SimpleImputer",
            "actually_imputed_features_and_train_medians": actually_imputed,
            "food_category": "Unknown when missing",
            "cooking_state": "deterministic keyword rule; never missing",
            "rows_removed_for_feature_missingness": 0,
        },
        "split": {
            "method": "GroupShuffleSplit by normalized food description",
            "random_state_train_holdout": RANDOM_STATE,
            "random_state_validation_test": RANDOM_STATE + 1,
            "sizes": split_sizes,
            "group_counts": split_group_counts,
            "group_overlap_counts": {
                "train_validation": 0,
                "train_test": 0,
                "validation_test": 0,
            },
        },
        "leakage_controls": {
            "target_selection": "Only nutrient_nbr 208 Energy [KCAL]",
            "excluded_target_nutrients": [
                "957 Energy (Atwater General Factors) [KCAL]",
                "958 Energy (Atwater Specific Factors) [KCAL]",
            ],
            "excluded_feature_nutrients": [
                "208 Energy [KCAL]",
                "268 Energy [kJ]",
                "957/958 Atwater-derived energy",
                "all energy-derived columns",
            ],
            "preprocessing_fit_scope": "training split only",
            "model_selection_scope": "validation RMSE only",
        },
        "library_versions": versions,
    }

    metadata_files = []
    for key, model in fitted.items():
        model_path = model_dir / f"{key}.joblib"
        joblib.dump(model, model_path)
        metadata = {
            **common_metadata,
            "model_key": key,
            "algorithm": model_specs[key]["algorithm"],
            "hyperparameters": model_specs[key]["hyperparameters"],
            "metrics": metrics[key],
            "fit_seconds": fit_seconds[key],
            "model_file": str(model_path.relative_to(project_root)).replace("\\", "/"),
            "selected_best_model": key == best_model,
        }
        metadata_path = model_dir / f"{key}_metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        metadata_files.append(str(metadata_path.relative_to(project_root)).replace("\\", "/"))

    aggregate_metadata = {
        **common_metadata,
        "models": model_specs,
        "metrics": metrics,
        "fit_seconds": fit_seconds,
        "best_model_by_validation_rmse": best_model,
        "artifacts": {
            "feature_matrix": "data/processed/regression_features.csv",
            "split_assignments": "data/processed/regression_split_assignments.csv",
            "figure": str(figure_path.relative_to(project_root)).replace("\\", "/"),
            "model_metadata_files": metadata_files,
        },
    }
    aggregate_path = model_dir / "experiment_metadata.json"
    aggregate_path.write_text(
        json.dumps(aggregate_metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    command = (
        "D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer/.venv/"
        "Scripts/python.exe training/regression/run_experiment.py --project-root "
        "D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer"
    )
    report = create_report(
        command=command,
        generated_at=generated_at,
        join_audit=join_audit,
        source_audits=source_audits,
        feature_matrix=matrix,
        split_sizes=split_sizes,
        split_group_counts=split_group_counts,
        missing_totals=missing_totals,
        imputer_medians=imputer_medians,
        metrics=metrics,
        fit_seconds=fit_seconds,
        best_model=best_model,
        figure_relative_path=(
            "figures/" + figure_path.name
        ),
        versions=versions,
    )
    report_path = report_dir / "regression_experiment.md"
    report_path.write_text(report, encoding="utf-8")

    print("BEST_MODEL=" + best_model)
    print("SPLIT_SIZES=" + json.dumps(split_sizes))
    print("MISSING_TOTALS=" + json.dumps(missing_totals))
    print("IMPUTER_TRAIN_MEDIANS=" + json.dumps(actually_imputed))
    print("ARTIFACTS_WRITTEN=" + json.dumps(aggregate_metadata["artifacts"]))


if __name__ == "__main__":
    main()
