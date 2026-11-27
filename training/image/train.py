"""Huấn luyện MobileNetV3-Small nhận diện món ăn bằng transfer learning (§5.1).

Vì sao MobileNetV3-Small + CPU: xem docs/TECHNICAL_DECISIONS.md (TD-03) - GPU Quadro P2000
là kiến trúc Pascal sm_61, các bản PyTorch CUDA hiện hành không còn build cho nó.

Dữ liệu đầu vào: data/processed/image_dataset_manifest.csv (do training/image/prepare_dataset.py
sinh ra). Nếu chưa có manifest, script quét data/raw/images/<lớp>/ và tự chia tập theo seed.

Cách dùng:
    .venv\\Scripts\\python.exe training\\image\\train.py                  # cấu hình mặc định
    .venv\\Scripts\\python.exe training\\image\\train.py --epochs 15 --batch-size 16
    .venv\\Scripts\\python.exe training\\image\\train.py --limit-per-class 50 --epochs 2  # chạy thử
    .venv\\Scripts\\python.exe training\\image\\train.py --no-pretrained                  # không tải trọng số ImageNet

Kết quả:
    models/image/best.pt        trọng số model tốt nhất + danh sách nhãn (đúng hợp đồng app/ml)
    models/image/latest.json    metadata: metrics THẬT, thời gian, dataset, thư viện
    data/reports/image_experiment.md   báo cáo thực nghiệm (chỉ số đo được)
    data/reports/figures/       biểu đồ đường cong huấn luyện + ma trận nhầm lẫn
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

DEFAULT_RAW_DIR = BASE_DIR / "data" / "raw" / "images"
DEFAULT_MANIFEST = BASE_DIR / "data" / "processed" / "image_dataset_manifest.csv"
DEFAULT_OUT_DIR = BASE_DIR / "models" / "image"
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


# --------------------------------------------------------------------------- dữ liệu


def scan_raw_images(raw_dir: Path) -> list[tuple[Path, str]]:
    items: list[tuple[Path, str]] = []
    if not raw_dir.exists():
        return items
    for class_dir in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
        for path in sorted(class_dir.rglob("*")):
            if path.suffix.lower() in IMAGE_EXTENSIONS and path.is_file():
                items.append((path, class_dir.name))
    return items


def load_manifest(manifest: Path, raw_dir: Path) -> list[tuple[Path, str, str]]:
    """Đọc manifest CSV -> [(đường_dẫn, lớp, split)]."""
    import csv

    rows: list[tuple[Path, str, str]] = []
    with manifest.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rel = (row.get("relative_path") or "").strip()
            label = (row.get("our_class") or row.get("label") or "").strip()
            split = (row.get("split") or "").strip().lower()
            if not rel or not label:
                continue
            path = Path(rel)
            if not path.is_absolute():
                candidate = raw_dir / rel
                if not candidate.exists():
                    candidate = raw_dir / label / Path(rel).name
                path = candidate
            if path.exists():
                rows.append((path, label, split if split in {"train", "val", "test", "validation"} else ""))
    return rows


def build_splits(
    rows: list[tuple[Path, str, str]],
    seed: int,
    val_ratio: float,
    test_ratio: float,
    limit_per_class: int | None,
) -> dict[str, list[tuple[Path, str]]]:
    """Chia tập. Nếu manifest đã có cột split thì tôn trọng; nếu không thì chia theo seed."""
    rng = random.Random(seed)
    by_class: dict[str, list[tuple[Path, str, str]]] = defaultdict(list)
    for row in rows:
        by_class[row[1]].append(row)

    splits: dict[str, list[tuple[Path, str]]] = {"train": [], "val": [], "test": []}
    for label, items in sorted(by_class.items()):
        if limit_per_class:
            items = items[:limit_per_class]
        pre_split = [i for i in items if i[2]]
        if pre_split and len(pre_split) == len(items):
            for path, lab, split in items:
                splits["val" if split == "validation" else split].append((path, lab))
            continue
        shuffled = items[:]
        rng.shuffle(shuffled)
        n_test = int(round(len(shuffled) * test_ratio))
        n_val = int(round(len(shuffled) * val_ratio))
        splits["test"].extend((p, l) for p, l, _ in shuffled[:n_test])
        splits["val"].extend((p, l) for p, l, _ in shuffled[n_test:n_test + n_val])
        splits["train"].extend((p, l) for p, l, _ in shuffled[n_test + n_val:])
    return splits


class ImageListDataset:
    """Dataset đơn giản đọc danh sách (đường dẫn, nhãn) - không phụ thuộc cấu trúc thư mục."""

    def __init__(self, items: list[tuple[Path, str]], classes: list[str], transform) -> None:
        self.items = items
        self.class_to_idx = {c: i for i, c in enumerate(classes)}
        self.transform = transform

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int):
        from PIL import Image

        path, label = self.items[index]
        with Image.open(path) as img:
            tensor = self.transform(img.convert("RGB"))
        return tensor, self.class_to_idx[label]


# --------------------------------------------------------------------------- huấn luyện


def build_model(num_classes: int, pretrained: bool):
    import torch.nn as nn
    from torchvision import models as tvm

    weights = tvm.MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
    net = tvm.mobilenet_v3_small(weights=weights)
    in_features = net.classifier[-1].in_features
    net.classifier[-1] = nn.Linear(in_features, num_classes)
    return net


def evaluate(model, loader, criterion, device) -> tuple[float, float, list, list]:
    import torch

    model.eval()
    total_loss = 0.0
    correct = 0
    seen = 0
    y_true: list[int] = []
    y_pred: list[int] = []
    with torch.no_grad():
        for images, targets in loader:
            images, targets = images.to(device), targets.to(device)
            logits = model(images)
            loss = criterion(logits, targets)
            total_loss += float(loss.item()) * images.size(0)
            preds = logits.argmax(dim=1)
            correct += int((preds == targets).sum().item())
            seen += images.size(0)
            y_true.extend(targets.cpu().tolist())
            y_pred.extend(preds.cpu().tolist())
    if seen == 0:
        return 0.0, 0.0, [], []
    return total_loss / seen, correct / seen, y_true, y_pred


def main() -> int:
    parser = argparse.ArgumentParser(description="Huấn luyện MobileNetV3-Small nhận diện món ăn")
    parser.add_argument("--epochs", type=int, default=15, help="Số epoch tối đa (§5.1: 10-20)")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size (§5.1: 8-16)")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate khi fine-tune")
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--patience", type=int, default=4, help="Early stopping: số epoch chờ")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--limit-per-class", type=int, default=None, help="Giới hạn ảnh mỗi lớp")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--no-pretrained", action="store_true", help="Không dùng trọng số ImageNet")
    parser.add_argument("--device", default="cpu", help="Mặc định cpu (xem TD-03)")
    parser.add_argument("--class-weights", choices=("none", "balanced"), default="none",
                        help="'balanced' = trọng số lớp nghịch với số ảnh train, chống lệch lớp "
                             "(các lớp món Việt chỉ có ~25 ảnh trong khi lớp Food-101 có 70 ảnh)")
    args = parser.parse_args()

    import numpy as np
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader
    from torchvision import transforms

    torch.manual_seed(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.set_num_threads(min(8, os.cpu_count() or 4))

    manifest = Path(args.manifest)
    raw_dir = Path(args.raw_dir)
    rows: list[tuple[Path, str, str]]
    source_note: str
    if manifest.exists():
        rows = load_manifest(manifest, raw_dir)
        source_note = f"manifest {manifest} ({len(rows)} ảnh)"
    else:
        scanned = scan_raw_images(raw_dir)
        rows = [(p, label, "") for p, label in scanned]
        source_note = f"quét thư mục {raw_dir} ({len(rows)} ảnh, chưa có manifest)"

    if not rows:
        print("[X] Không tìm thấy ảnh huấn luyện.")
        print(f"    Đã kiểm tra: {manifest} và {raw_dir}")
        print("    Hãy chạy training/image/prepare_dataset.py trước để thu thập ảnh.")
        return 2

    splits = build_splits(rows, args.seed, args.val_ratio, args.test_ratio, args.limit_per_class)
    labels_present = sorted({label for items in splits.values() for _, label in items})
    if len(labels_present) < 2:
        print(f"[X] Cần tối thiểu 2 lớp để phân loại, hiện có {len(labels_present)}: {labels_present}")
        return 2
    if not splits["train"] or not splits["val"]:
        print("[X] Thiếu dữ liệu train hoặc validation sau khi chia tập.")
        return 2

    print("=" * 68)
    print("  HUẤN LUYỆN MobileNetV3-Small - NHẬN DIỆN MÓN ĂN")
    print(f"  Nguồn dữ liệu : {source_note}")
    print(f"  Số lớp        : {len(labels_present)} -> {labels_present}")
    for name in ("train", "val", "test"):
        print(f"  {name:13s}: {len(splits[name])} ảnh")
    print(f"  Thiết bị      : {args.device} | epoch tối đa {args.epochs} | batch {args.batch_size}")
    print("=" * 68)

    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(224, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.RandomRotation(12),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        # Xoá ngẫu nhiên một mảng nhỏ: model phải dựa vào nhiều vùng ảnh thay vì một chi tiết.
        transforms.RandomErasing(p=0.25, scale=(0.02, 0.12), value="random"),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])

    train_ds = ImageListDataset(splits["train"], labels_present, train_tf)
    val_ds = ImageListDataset(splits["val"], labels_present, eval_tf)
    test_ds = ImageListDataset(splits["test"], labels_present, eval_tf)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    model = build_model(len(labels_present), pretrained=not args.no_pretrained)
    model.to(args.device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    loss_note = "CrossEntropyLoss(label_smoothing=0.1)"
    if args.class_weights == "balanced":
        # Lớp món Việt chỉ có ~25 ảnh train trong khi lớp Food-101 có 70 ảnh: không cân bằng thì
        # model nghiêng về lớp nhiều ảnh và các lớp món Việt (đặc biệt nhóm món nước) bị hút mất.
        label_to_idx = {label: index for index, label in enumerate(labels_present)}
        counts = np.zeros(len(labels_present), dtype=np.float64)
        for _path, label in splits["train"]:
            counts[label_to_idx[label]] += 1.0
        counts[counts == 0] = 1.0
        weights = counts.sum() / (len(counts) * counts)
        criterion = nn.CrossEntropyLoss(
            weight=torch.tensor(weights, dtype=torch.float32, device=args.device),
            label_smoothing=0.1)
        loss_note = "CrossEntropyLoss(weight=balanced, label_smoothing=0.1)"
        print("  trọng số lớp (balanced):")
        for index, label in enumerate(labels_present):
            print(f"    {label:18} {int(counts[index]):3} ảnh train | trọng số {weights[index]:.3f}")
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, args.epochs))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir = Path(args.report_dir)
    (report_dir / "figures").mkdir(parents=True, exist_ok=True)

    history: list[dict] = []
    best_val_acc = -1.0
    best_val_loss = float("inf")
    best_epoch = -1
    epochs_without_improvement = 0
    started = time.perf_counter()

    for epoch in range(1, args.epochs + 1):
        model.train()
        epoch_started = time.perf_counter()
        running_loss = 0.0
        seen = 0
        correct = 0
        for images, targets in train_loader:
            images, targets = images.to(args.device), targets.to(args.device)
            optimizer.zero_grad()
            logits = model(images)
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()
            running_loss += float(loss.item()) * images.size(0)
            correct += int((logits.argmax(dim=1) == targets).sum().item())
            seen += images.size(0)
        scheduler.step()

        train_loss = running_loss / max(1, seen)
        train_acc = correct / max(1, seen)
        val_loss, val_acc, _, _ = evaluate(model, val_loader, criterion, args.device)
        elapsed = time.perf_counter() - epoch_started

        history.append({
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "train_accuracy": round(train_acc, 4),
            "val_loss": round(val_loss, 4),
            "val_accuracy": round(val_acc, 4),
            "seconds": round(elapsed, 1),
        })
        print(f"  epoch {epoch:2d}/{args.epochs} | train loss {train_loss:.4f} acc {train_acc:.3f} "
              f"| val loss {val_loss:.4f} acc {val_acc:.3f} | {elapsed:.1f}s")

        improved = val_acc > best_val_acc or (val_acc == best_val_acc and val_loss < best_val_loss)
        if improved:
            best_val_acc, best_val_loss, best_epoch = val_acc, val_loss, epoch
            epochs_without_improvement = 0
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "labels": labels_present,
                    "arch": "mobilenet_v3_small",
                    "input_size": 224,
                    "epoch": epoch,
                },
                out_dir / "best.pt",
            )
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= args.patience:
                print(f"  -> Dừng sớm: không cải thiện trong {args.patience} epoch.")
                break

    total_seconds = time.perf_counter() - started

    # đánh giá trên tập test bằng trọng số tốt nhất
    checkpoint = torch.load(out_dir / "best.pt", map_location=args.device, weights_only=False)
    model.load_state_dict(checkpoint["state_dict"])
    test_loss, test_acc, y_true, y_pred = evaluate(model, test_loader, criterion, args.device)

    per_class: list[dict] = []
    for idx, label in enumerate(labels_present):
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == idx and p == idx)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != idx and p == idx)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == idx and p != idx)
        support = sum(1 for t in y_true if t == idx)
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        f1 = (2 * precision * recall / (precision + recall)) if precision and recall else None
        per_class.append({
            "label": label,
            "support": support,
            "precision": None if precision is None else round(precision, 4),
            "recall": None if recall is None else round(recall, 4),
            "f1": None if f1 is None else round(f1, 4),
        })
    macro_f1 = None
    f1_values = [c["f1"] for c in per_class if c["f1"] is not None]
    if f1_values:
        macro_f1 = round(sum(f1_values) / len(f1_values), 4)

    confusion = [[0] * len(labels_present) for _ in labels_present]
    for t, p in zip(y_true, y_pred):
        confusion[t][p] += 1

    metadata = {
        "arch": "mobilenet_v3_small",
        "input_size": 224,
        "labels": labels_present,
        "num_classes": len(labels_present),
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "device": args.device,
        "hyperparameters": {
            "epochs_max": args.epochs,
            "epochs_run": len(history),
            "best_epoch": best_epoch,
            "batch_size": args.batch_size,
            "learning_rate": args.lr,
            "weight_decay": args.weight_decay,
            "optimizer": "AdamW",
            "loss": loss_note,
            "scheduler": "CosineAnnealingLR",
            "pretrained": not args.no_pretrained,
            "early_stopping_patience": args.patience,
            "seed": args.seed,
        },
        "dataset": {
            "source_note": source_note,
            "counts": {name: len(splits[name]) for name in ("train", "val", "test")},
            "per_class_counts": {
                label: {
                    "train": sum(1 for _, l in splits["train"] if l == label),
                    "val": sum(1 for _, l in splits["val"] if l == label),
                    "test": sum(1 for _, l in splits["test"] if l == label),
                }
                for label in labels_present
            },
        },
        "metrics": {
            "best_val_accuracy": round(best_val_acc, 4),
            "best_val_loss": round(best_val_loss, 4),
            "test_loss": round(test_loss, 4),
            "test_accuracy": round(test_acc, 4),
            "test_macro_f1": macro_f1,
            "test_per_class": per_class,
            "confusion_matrix": confusion,
        },
        "timing": {
            "total_seconds": round(total_seconds, 1),
            "seconds_per_epoch": [h["seconds"] for h in history],
        },
        "history": history,
        "library_versions": {
            "torch": torch.__version__,
            "python": platform.python_version(),
        },
    }
    (out_dir / "latest.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ---------- biểu đồ ----------
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        epochs_axis = [h["epoch"] for h in history]
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        axes[0].plot(epochs_axis, [h["train_loss"] for h in history], marker="o", label="train")
        axes[0].plot(epochs_axis, [h["val_loss"] for h in history], marker="s", label="validation")
        axes[0].set_xlabel("Epoch")
        axes[0].set_ylabel("Loss")
        axes[0].set_title("Đường cong mất mát")
        axes[0].legend()
        axes[0].grid(alpha=0.3)
        axes[1].plot(epochs_axis, [h["train_accuracy"] for h in history], marker="o", label="train")
        axes[1].plot(epochs_axis, [h["val_accuracy"] for h in history], marker="s", label="validation")
        axes[1].set_xlabel("Epoch")
        axes[1].set_ylabel("Accuracy")
        axes[1].set_title("Độ chính xác")
        axes[1].legend()
        axes[1].grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(report_dir / "figures" / "image_training_curves.png", dpi=120)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(max(5, len(labels_present) * 0.9), max(4, len(labels_present) * 0.8)))
        im = ax.imshow(confusion, cmap="Blues")
        ax.set_xticks(range(len(labels_present)), labels_present, rotation=45, ha="right")
        ax.set_yticks(range(len(labels_present)), labels_present)
        ax.set_xlabel("Dự đoán")
        ax.set_ylabel("Thực tế")
        ax.set_title("Ma trận nhầm lẫn (tập test)")
        for i in range(len(labels_present)):
            for j in range(len(labels_present)):
                ax.text(j, i, str(confusion[i][j]), ha="center", va="center",
                        color="white" if confusion[i][j] > (max(max(r) for r in confusion) / 2) else "black")
        fig.colorbar(im, ax=ax)
        fig.tight_layout()
        fig.savefig(report_dir / "figures" / "image_confusion_matrix.png", dpi=120)
        plt.close(fig)
        figures_note = "data/reports/figures/image_training_curves.png, image_confusion_matrix.png"
    except Exception as exc:  # pragma: no cover - biểu đồ không bắt buộc
        figures_note = f"(không vẽ được biểu đồ: {type(exc).__name__})"

    # ---------- báo cáo ----------
    lines = [
        "# BÁO CÁO THỰC NGHIỆM – NHẬN DIỆN MÓN ĂN BẰNG ẢNH",
        "",
        f"- Thời điểm chạy (UTC): {metadata['trained_at']}",
        f"- Kiến trúc: MobileNetV3-Small (transfer learning từ ImageNet: "
        f"{'có' if not args.no_pretrained else 'KHÔNG'})",
        f"- Thiết bị: **{args.device}**" + (
            " (GPU Quadro P2000 · Pascal sm_61 — dùng bản PyTorch cu121 vì các bản CUDA mới hơn đã bỏ Pascal)"
            if args.device.startswith("cuda") else
            " (TD-03: lần huấn luyện ghi trong báo cáo này chạy trên CPU; GPU dùng được nếu cài "
            "PyTorch bản cu121, xem mục 7.6 của BAO_CAO_KIEM_THU.md)"
        ),
        f"- Nguồn dữ liệu: {source_note}",
        f"- Số lớp: **{len(labels_present)}**",
        f"- Thời gian huấn luyện: **{total_seconds:.1f} s** cho {len(history)} epoch "
        f"({', '.join(str(h['seconds']) for h in history)} giây/epoch)",
        "",
        "## 1. Kích thước tập dữ liệu",
        "",
        "| Tập | Số ảnh |",
        "|---|---|",
        f"| train | {len(splits['train'])} |",
        f"| validation | {len(splits['val'])} |",
        f"| test | {len(splits['test'])} |",
        "",
        "## 2. Kết quả",
        "",
        "| Chỉ số | Giá trị |",
        "|---|---|",
        f"| Accuracy tốt nhất trên validation | **{best_val_acc:.4f}** (epoch {best_epoch}) |",
        f"| Loss tốt nhất trên validation | {best_val_loss:.4f} |",
        f"| **Accuracy trên tập test** | **{test_acc:.4f}** |",
        f"| Loss trên tập test | {test_loss:.4f} |",
        f"| Macro F1 trên tập test | {macro_f1 if macro_f1 is not None else 'không tính được'} |",
        "",
        "## 3. Chỉ số theo từng lớp (tập test)",
        "",
        "| Lớp | Số mẫu | Precision | Recall | F1 |",
        "|---|---|---|---|---|",
    ]
    for c in per_class:
        lines.append(
            f"| {c['label']} | {c['support']} | "
            f"{c['precision'] if c['precision'] is not None else '-'} | "
            f"{c['recall'] if c['recall'] is not None else '-'} | "
            f"{c['f1'] if c['f1'] is not None else '-'} |"
        )
    lines += [
        "",
        "## 4. Lịch sử huấn luyện",
        "",
        "| Epoch | Train loss | Train acc | Val loss | Val acc | Giây |",
        "|---|---|---|---|---|---|",
    ]
    for h in history:
        lines.append(
            f"| {h['epoch']} | {h['train_loss']} | {h['train_accuracy']} | "
            f"{h['val_loss']} | {h['val_accuracy']} | {h['seconds']} |"
        )
    lines += [
        "",
        "## 5. Biểu đồ",
        "",
        f"- {figures_note}",
        "",
        "## 6. Ghi chú trung thực về kết quả",
        "",
        "- Toàn bộ số liệu trong báo cáo này do chính lần chạy trên sinh ra, không nhập tay.",
        "- Độ chính xác phụ thuộc hoàn toàn vào dữ liệu đã huấn luyện. Số lớp thực tế có thể "
        "ít hơn 15 lớp mục tiêu của đề bài nếu thiếu ảnh (xem data/reports/image_dataset_report.md).",
        "- Food-101 chỉ phủ chính xác 4/15 lớp món ăn mục tiêu; ảnh món Việt Nam phải thu thập "
        "riêng từ Wikimedia Commons (xem data/reports/sourcing_report.md).",
        "- Không được trích dẫn kết quả này cho một lớp chưa từng có ảnh huấn luyện.",
    ]
    (report_dir / "image_experiment.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n" + "=" * 68)
    print(f"  Kết quả: accuracy test = {test_acc:.4f} | macro F1 = {macro_f1}")
    print(f"  Model  : {out_dir / 'best.pt'}")
    print(f"  Metadata: {out_dir / 'latest.json'}")
    print(f"  Báo cáo : {report_dir / 'image_experiment.md'}")
    print(f"  Thời gian: {total_seconds:.1f} s")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
