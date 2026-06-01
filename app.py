from flask import Flask, render_template, jsonify, request, send_from_directory
from pathlib import Path
from PIL import Image
import xml.etree.ElementTree as ET
import webbrowser
import threading
import json
import os
import signal
import subprocess
import sys
import csv

app = Flask(__name__)

# ============================================================
# 路徑設定：全部使用相對路徑，不寫死電腦路徑
# ============================================================
BASE = Path(__file__).resolve().parent

IMG_DIR = BASE / "images"
YOLO_DIR = BASE / "yolo_labels"
XML_DIR = BASE / "output_xml"
STATUS_DIR = BASE / "status"
MANIFEST_PATH = BASE / "image_manifest.csv"

for p in [IMG_DIR, YOLO_DIR, XML_DIR, STATUS_DIR]:
    p.mkdir(exist_ok=True)

# ============================================================
# 類別設定
# general model + other model
# ============================================================
CLASSES = [
    "rDA09","rDB01","rDF02","rDP03","rDR04","rDS05","rDS06","rDU11","rDX07","rDX08",
    "rIC05","rIC07","rIC27","rID13","rIH03","rIH04","rIH06","rIH11","rIH12","rIH14",
    "rIH17","rIH18","rIH19","rIH21","rIH25","rIL01","rIL02","rIL08","rIL10","rIL15",
    "rIL23","rIL24","rIL26","rIO09",
    "OT07","OT10"
]

ZH = {
    "rDA09":"白尖病",
    "rDB01":"胡麻葉枯病",
    "rDF02":"徒長病",
    "rDP03":"稻熱病",
    "rDR04":"紋枯病",
    "rDS05":"葉鞘腐敗病",
    "rDS06":"白絹病",
    "rDU11":"稻麴病",
    "rDX07":"白葉枯病",
    "rDX08":"細菌性條斑病",

    "rIC05":"水稻水象鼻蟲",
    "rIC07":"負泥蟲",
    "rIC27":"鐵甲蟲",
    "rID13":"稻心蠅",

    "rIH03":"南方綠椿象",
    "rIH04":"褐飛蝨",
    "rIH06":"黑椿象",
    "rIH11":"黑尾葉蟬",
    "rIH12":"稻椿象",
    "rIH14":"緣椿象",
    "rIH17":"斑飛蝨",
    "rIH18":"蚜蟲",
    "rIH19":"細針緣椿象",
    "rIH21":"白背飛蝨",
    "rIH25":"白星椿象",

    "rIL01":"大螟與二化螟",
    "rIL02":"稻縱捲葉蟲",
    "rIL08":"暮眼蝶",
    "rIL10":"斜紋夜蛾",
    "rIL15":"弄蝶",
    "rIL23":"毒蛾類",
    "rIL24":"麥蛾",
    "rIL26":"分秘夜蛾",

    "rIO09":"水稻蝗蟲",

    "OT07":"福壽螺",
    "OT10":"藥害"
}

CLASS_TO_ID = {c: i for i, c in enumerate(CLASSES)}

# ============================================================
# 工具函式
# ============================================================
def get_status_map():
    status = {}

    for p in IMG_DIR.glob("*"):
        if p.suffix.lower() not in [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"]:
            continue

        status_file = STATUS_DIR / f"{p.stem}.json"

        if status_file.exists():
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    status[p.name] = json.load(f)
            except Exception:
                status[p.name] = {
                    "reviewed": False,
                    "modified": False
                }
        else:
            status[p.name] = {
                "reviewed": False,
                "modified": False
            }

    return status


def get_original_info(filename):
    default_info = {
        "batch_id": "",
        "serial_id": "",
        "serial_filename": filename,
        "original_filename": filename,
        "original_path": filename,
        "original_folder": ""
    }

    if not MANIFEST_PATH.exists():
        return default_info

    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                if row.get("serial_filename", "") == filename:
                    return {
                        "batch_id": row.get("batch_id", ""),
                        "serial_id": row.get("serial_id", ""),
                        "serial_filename": row.get("serial_filename", filename),
                        "original_filename": row.get("original_filename", filename),
                        "original_path": row.get("original_path", filename),
                        "original_folder": row.get("original_folder", "")
                    }

    except Exception:
        return default_info

    return default_info


def read_xml_boxes(xml_path):
    """
    已審核過的 XML 優先讀取。
    這樣刪掉或修改過的框，不會重開後又從 YOLO txt 回來。
    """
    boxes = []

    tree = ET.parse(xml_path)
    root = tree.getroot()

    for obj in root.findall("object"):
        label = obj.findtext("name", "").strip()
        bnd = obj.find("bndbox")

        if not label or bnd is None:
            continue

        try:
            xmin = int(float(bnd.findtext("xmin", 0)))
            ymin = int(float(bnd.findtext("ymin", 0)))
            xmax = int(float(bnd.findtext("xmax", 0)))
            ymax = int(float(bnd.findtext("ymax", 0)))
        except Exception:
            continue

        boxes.append({
            "label": label,
            "zh": ZH.get(label, label),
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmax,
            "ymax": ymax,
            "source": "expert"
        })

    return boxes


def parse_yolo_label_token(token):
    """
    支援兩種格式：
    1. numeric class id:
       3 0.5 0.5 0.2 0.2

    2. code label:
       rDP03 0.5 0.5 0.2 0.2
       OT07 0.5 0.5 0.2 0.2
    """
    token = token.strip()

    # code-based label
    if token in CLASS_TO_ID:
        return token

    # numeric class id
    try:
        cls_id = int(float(token))
        if 0 <= cls_id < len(CLASSES):
            return CLASSES[cls_id]
    except Exception:
        return None

    return None


def read_yolo_boxes(label_path, w, h):
    boxes = []

    if not label_path.exists():
        return boxes

    try:
        lines = label_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return boxes

    for line in lines:
        p = line.strip().split()

        if len(p) < 5:
            continue

        label = parse_yolo_label_token(p[0])

        if label is None:
            continue

        try:
            xc, yc, bw, bh = map(float, p[1:5])
        except Exception:
            continue

        xmin = int((xc - bw / 2) * w)
        ymin = int((yc - bh / 2) * h)
        xmax = int((xc + bw / 2) * w)
        ymax = int((yc + bh / 2) * h)

        xmin = max(0, min(xmin, w - 1))
        xmax = max(0, min(xmax, w - 1))
        ymin = max(0, min(ymin, h - 1))
        ymax = max(0, min(ymax, h - 1))

        if xmax <= xmin or ymax <= ymin:
            continue

        boxes.append({
            "label": label,
            "zh": ZH.get(label, label),
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmax,
            "ymax": ymax,
            "source": "ai"
        })

    return boxes


def open_folder(path):
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform.startswith("darwin"):
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def add_basic_info_fields(obj):
    for i in range(1, 10):
        ET.SubElement(obj, f"Basic_Info_{i}").text = "0"


# ============================================================
# Routes
# ============================================================
@app.route("/")
def index():
    images = sorted([
        p.name for p in IMG_DIR.glob("*")
        if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"]
    ])

    return render_template(
        "index.html",
        images=images,
        status_map=get_status_map(),
        classes=CLASSES,
        zh=ZH
    )


@app.route("/image/<filename>")
def image_file(filename):
    return send_from_directory(IMG_DIR, filename)


@app.route("/load/<filename>")
def load_image(filename):
    img_path = IMG_DIR / filename

    if not img_path.exists():
        return jsonify({
            "error": "image not found",
            "filename": filename,
            "boxes": []
        }), 404

    img = Image.open(img_path)
    w, h = img.size

    xml_path = XML_DIR / f"{Path(filename).stem}.xml"
    yolo_path = YOLO_DIR / f"{Path(filename).stem}.txt"

    if xml_path.exists():
        boxes = read_xml_boxes(xml_path)
        source_type = "xml"
    else:
        boxes = read_yolo_boxes(yolo_path, w, h)
        source_type = "yolo"

    return jsonify({
        "filename": filename,
        "width": w,
        "height": h,
        "boxes": boxes,
        "source_type": source_type
    })


@app.route("/save", methods=["POST"])
def save():
    data = request.json

    filename = data["filename"]
    width = data["width"]
    height = data["height"]
    boxes = data["boxes"]
    modified = data.get("modified", False)

    original_info = get_original_info(filename)

    annotation = ET.Element("annotation")

    folder = ET.SubElement(annotation, "folder")
    folder.text = original_info["original_path"]

    crop = ET.SubElement(annotation, "Crop")
    crop.text = "rice"

    fname = ET.SubElement(annotation, "filename")
    fname.text = filename

    source = ET.SubElement(annotation, "source")
    database = ET.SubElement(source, "database")
    database.text = "Unknown"

    size = ET.SubElement(annotation, "size")
    ET.SubElement(size, "width").text = str(width)
    ET.SubElement(size, "height").text = str(height)
    ET.SubElement(size, "depth").text = "3"

    ET.SubElement(annotation, "segmented").text = "0"

    original = ET.SubElement(annotation, "original")
    ET.SubElement(original, "batch_id").text = original_info["batch_id"]
    ET.SubElement(original, "serial_id").text = str(original_info["serial_id"])
    ET.SubElement(original, "serial_filename").text = original_info["serial_filename"]
    ET.SubElement(original, "original_filename").text = original_info["original_filename"]
    ET.SubElement(original, "original_path").text = original_info["original_path"]
    ET.SubElement(original, "original_folder").text = original_info["original_folder"]

    for b in boxes:
        obj = ET.SubElement(annotation, "object")

        ET.SubElement(obj, "name").text = b["label"]
        ET.SubElement(obj, "pose").text = "Unspecified"
        ET.SubElement(obj, "truncated").text = "0"
        ET.SubElement(obj, "difficult").text = "0"

        add_basic_info_fields(obj)

        bb = ET.SubElement(obj, "bndbox")
        ET.SubElement(bb, "xmin").text = str(int(b["xmin"]))
        ET.SubElement(bb, "ymin").text = str(int(b["ymin"]))
        ET.SubElement(bb, "xmax").text = str(int(b["xmax"]))
        ET.SubElement(bb, "ymax").text = str(int(b["ymax"]))

    out_xml = XML_DIR / f"{Path(filename).stem}.xml"

    tree = ET.ElementTree(annotation)

    # Python 3.9+ 支援 ET.indent
    try:
        ET.indent(tree, space="  ", level=0)
    except Exception:
        pass

    tree.write(
        out_xml,
        encoding="utf-8",
        xml_declaration=True
    )

    status_file = STATUS_DIR / f"{Path(filename).stem}.json"

    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "reviewed": True,
                "modified": bool(modified),
                "batch_id": original_info["batch_id"],
                "original_filename": original_info["original_filename"]
            },
            f,
            ensure_ascii=False,
            indent=2
        )

    return jsonify({
        "status": "ok",
        "xml": str(out_xml)
    })


@app.route("/open_folder/<folder>")
def open_folder_route(folder):
    mapping = {
        "images": IMG_DIR,
        "labels": YOLO_DIR,
        "xml": XML_DIR,
        "status": STATUS_DIR,
        "base": BASE,
        "raw": BASE / "Raw_Images",
        "models": BASE / "models"
    }

    path = mapping.get(folder)

    if path is None:
        return jsonify({
            "status": "error",
            "message": "unknown folder"
        })

    path.mkdir(exist_ok=True)

    try:
        open_folder(path)
        return jsonify({
            "status": "ok",
            "path": str(path)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })


@app.route("/shutdown", methods=["POST"])
def shutdown():
    def stop():
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Timer(0.5, stop).start()

    return jsonify({
        "status": "shutting_down"
    })


def open_browser():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )