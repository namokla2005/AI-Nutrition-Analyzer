# Pipeline hồi quy năng lượng

Chạy từ thư mục gốc dự án:

```bash
"D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer/.venv/Scripts/python.exe" training/regression/run_experiment.py --project-root "D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer"
```

Kiểm thử các quy tắc nối dữ liệu, loại rò rỉ và chia nhóm:

```bash
"D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer/.venv/Scripts/python.exe" -m unittest training/regression/tests/test_pipeline.py -v
```

Pipeline chỉ đọc `data/external/usda/` và ghi vào:

- `data/processed/regression_features.csv`
- `data/processed/regression_split_assignments.csv`
- `models/regression/`
- `data/reports/regression_experiment.md`
- `data/reports/figures/`

Các mô hình được lưu dưới dạng scikit-learn `Pipeline`, gồm tiền xử lý học riêng từ train và estimator đã fit.
