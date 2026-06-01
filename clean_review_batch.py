from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent

folders_to_clean = [
    "Raw_Images",
    "images",
    "yolo_labels",
    "output_xml",
    "status",
    "temp_predict"
]

for folder in folders_to_clean:
    p = BASE / folder
    if p.exists():
        for item in p.iterdir():
            if item.name == ".gitkeep":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    else:
        p.mkdir(parents=True, exist_ok=True)
    print("cleaned:", p)

manifest = BASE / "image_manifest.csv"
if manifest.exists():
    manifest.unlink()
    print("deleted:", manifest)

print("\n完成：已清空本批資料")
print("保留：app.py、prepare_and_predict.py、templates、static、batch_id.txt")