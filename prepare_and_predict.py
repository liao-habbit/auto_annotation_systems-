from pathlib import Path
from PIL import Image, ImageOps
from ultralytics import YOLO
import shutil
import pandas as pd
import gc
import torch

# =========================================================
# 路徑設定
# =========================================================
TOOL_DIR = Path(__file__).resolve().parent
RAW_DIR = TOOL_DIR / "Raw_Images"       #   原始影像
IMAGE_DIR = TOOL_DIR / "images"         #   輸出影像
LABEL_DIR = TOOL_DIR / "yolo_labels"    #   輸出每個物件框的 預測標籤 以及 物件框的位置 
MANIFEST_PATH = TOOL_DIR / "image_manifest.csv"  #    影像的流水號
BATCH_ID_PATH = TOOL_DIR / "batch_id.txt"        #    批次的文字編號

IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".heic", ".heif"]

# =========================================================
# 多模型設定
# 注意：
# other_OT07.pt 當初是 OT07 + OT10 訓練
# 所以 snail_classes.txt 必須是：
# OT07
# OT10
# 但這裡只保留 OT07
# =========================================================
MODELS = [                                                      # 影像標註模型
    {                                                           # 含有病害與蟲害
        "name": "general",
        "path": TOOL_DIR / "models" / "general.pt",
        "classes": TOOL_DIR / "models" / "general_classes.txt",
        "conf": 0.20,
        "iou": 0.50,
        "keep_labels": None
    },
    {                                                           # 僅含有 OT07(福壽螺)
        "name": "snail",
        "path": TOOL_DIR / "models" / "other_OT07.pt",
        "classes": TOOL_DIR / "models" / "snail_classes.txt",
        "conf": 0.20,
        "iou": 0.50,
        "keep_labels": ["OT07"]
    }
]

# =========================================================
# 讀取 Batch ID
# =========================================================
if BATCH_ID_PATH.exists():
    BATCH_ID = BATCH_ID_PATH.read_text(encoding="utf-8").strip()
else:
    BATCH_ID = "BATCH"

BATCH_ID = BATCH_ID.replace(" ", "_")
print("Batch ID:", BATCH_ID)

# =========================================================
# 工具函式
# =========================================================
def read_class_file(path):
    if not path.exists():
        raise FileNotFoundError(f"找不到 class file: {path}")

    classes = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            classes.append(line)
    if len(classes) == 0:
        raise ValueError(f"class file 是空的: {path}")
    return classes


def check_models():
    print("=" * 60)
    print("CHECK MODELS")
    print("=" * 60)

    for m in MODELS:
        if not m["path"].exists():
            print("找不到模型：", m["path"])
            raise SystemExit
        
        if not m["classes"].exists():
            print("找不到 classes.txt：", m["classes"])
            raise SystemExit

        m["class_list"] = read_class_file(m["classes"])

        print(f"[OK] {m['name']}")
        print(" model :", m["path"])
        print(" class :", m["classes"])
        print(" n_cls :", len(m["class_list"]))
        print(" keep  :", m["keep_labels"])


def yolo_xyxy_to_norm(xmin, ymin, xmax, ymax, w, h):
    x_center = ((xmin + xmax) / 2) / w
    y_center = ((ymin + ymax) / 2) / h
    bw = (xmax - xmin) / w
    bh = (ymax - ymin) / h

    x_center = max(0, min(1, x_center))
    y_center = max(0, min(1, y_center))
    bw = max(0, min(1, bw))
    bh = max(0, min(1, bh))

    return x_center, y_center, bw, bh


# =========================================================
# 清空舊資料
# =========================================================
print("=" * 60)
print("STEP 0 - 清空舊資料")
print("=" * 60)

for folder in [IMAGE_DIR, LABEL_DIR]:
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)

if MANIFEST_PATH.exists():
    MANIFEST_PATH.unlink()

RAW_DIR.mkdir(parents=True, exist_ok=True)

raw_images = [
    p for p in sorted(RAW_DIR.glob("*"))
    if p.suffix.lower() in IMAGE_EXTS
]

if len(raw_images) == 0:
    print("沒有找到任何圖片，請把照片放到：")
    print(RAW_DIR)
    raise SystemExit

print("找到原始圖片數：", len(raw_images))

# =========================================================
# Step 1 EXIF Normalize + 批次流水編號
# =========================================================
print()
print("=" * 60)
print("STEP 1 - EXIF 轉正 + 批次流水編號")
print("=" * 60)

manifest_rows = []
normalized_images = []

for idx, img_path in enumerate(raw_images, start=1):
    serial_name = f"{BATCH_ID}_{idx:06d}.jpg"
    out_path = IMAGE_DIR / serial_name

    try:
        img = Image.open(img_path)
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.save(out_path, quality=95)

        normalized_images.append(out_path)

        manifest_rows.append({
            "batch_id": BATCH_ID,
            "serial_id": idx,
            "serial_filename": serial_name,
            "original_filename": img_path.name,
            "original_path": str(img_path),
            "original_folder": str(img_path.parent)
        })

        if idx % 100 == 0:
            print(f"[{idx}/{len(raw_images)}] normalized")

    except Exception as e:
        print(f"[ERROR] {img_path.name}")
        print(e)

pd.DataFrame(manifest_rows).to_csv(
    MANIFEST_PATH,
    index=False,
    encoding="utf-8-sig"
)

print("Normalize 完成：", len(normalized_images))
print("Manifest saved:", MANIFEST_PATH)

if len(normalized_images) == 0:
    print("沒有可用圖片，停止。")
    raise SystemExit

# =========================================================
# Step 2 檢查模型
# =========================================================
print()
check_models()

# =========================================================
# Step 3 載入模型
# =========================================================
print()
print("=" * 60)
print("STEP 2 - Load YOLO Models")
print("=" * 60)

for m in MODELS:
    print("Loading:", m["name"])
    m["model"] = YOLO(m["path"])

# =========================================================
# Step 4 多模型預測並合併
# =========================================================
print()
print("=" * 60)
print("STEP 3 - Multi-model YOLO Predict")
print("=" * 60)

count_txt = 0
count_no_det = 0
count_error = 0
model_box_count = {m["name"]: 0 for m in MODELS}

for i, img_path in enumerate(normalized_images, start=1):
    try:
        img = Image.open(img_path)
        w, h = img.size

        merged_lines = []

        for m in MODELS:
            results = m["model"].predict(
                source=str(img_path),
                imgsz=640,
                conf=m["conf"],
                iou=m["iou"],
                save=False,
                save_txt=False,
                save_conf=False,
                verbose=False
            )

            r = results[0]

            if r.boxes is not None and len(r.boxes) > 0:
                for box in r.boxes:
                    local_cls_id = int(box.cls[0].item())

                    if local_cls_id < 0 or local_cls_id >= len(m["class_list"]):
                        continue

                    label_code = m["class_list"][local_cls_id]

                    if m["keep_labels"] is not None:
                        if label_code not in m["keep_labels"]:
                            continue

                    xmin, ymin, xmax, ymax = box.xyxy[0].cpu().numpy()

                    xmin = max(0, min(float(xmin), w - 1))
                    xmax = max(0, min(float(xmax), w - 1))
                    ymin = max(0, min(float(ymin), h - 1))
                    ymax = max(0, min(float(ymax), h - 1))

                    if xmax <= xmin or ymax <= ymin:
                        continue

                    x_center, y_center, bw, bh = yolo_xyxy_to_norm(
                        xmin, ymin, xmax, ymax, w, h
                    )

                    # =====================================================
                    # 重要：
                    # 這裡輸出 label_code，而不是數字 class id。
                    # app.py 需要能讀取 code-based YOLO label：
                    # OT07 0.5 0.5 0.2 0.2
                    # rDP03 0.5 0.5 0.2 0.2
                    # 這樣多模型 class id 不會互相衝突。
                    # =====================================================
                    merged_lines.append(
                        f"{label_code} {x_center:.6f} {y_center:.6f} {bw:.6f} {bh:.6f}"
                    )

                    model_box_count[m["name"]] += 1

            del results
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        txt_path = LABEL_DIR / f"{img_path.stem}.txt"

        if len(merged_lines) > 0:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(merged_lines))

            count_txt += 1
        else:
            count_no_det += 1

        if i % 50 == 0:
            print(f"[{i}/{len(normalized_images)}] labels={count_txt} | no_det={count_no_det}")

    except Exception as e:
        count_error += 1
        print(f"[ERROR] predict failed: {img_path.name}")
        print(e)

# =========================================================
# Done
# =========================================================
print()
print("=" * 60)
print("全部完成")
print("=" * 60)
print("Batch ID：", BATCH_ID)
print("圖片數：", len(normalized_images))
print("有偵測 txt：", count_txt)
print("無偵測：", count_no_det)
print("錯誤：", count_error)

print()
print("各模型保留框數：")
for k, v in model_box_count.items():
    print(f"{k}: {v}")

print()
print("請執行 run_tool.bat 開始人工審核")