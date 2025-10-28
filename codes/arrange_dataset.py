import os
import shutil
import pandas as pd
import pydicom
from collections import defaultdict

class c:
    OK = '\033[92m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    INFO = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

base_path = os.path.abspath("Datasets")
arranged_path = os.path.abspath("Arranged_datasets")
os.makedirs(arranged_path, exist_ok=True)

def safe_copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
        print(f"{c.INFO}→ Copied:{c.RESET} {os.path.relpath(src, base_path)} → {os.path.relpath(dst, arranged_path)}")

def extract_dicom_info(dicom_file):
    info = {"contrast": "", "dose": "", "filter": "", "direction": ""}
    try:
        dcm = pydicom.dcmread(dicom_file, stop_before_pixels=True)
        info["contrast"] = str(dcm.get("ContrastBolusAgent", "")).lower()
        info["dose"] = str(dcm.get("KVP", "")).lower()
        info["filter"] = str(dcm.get("ConvolutionKernel", "")).lower()
        info["direction"] = str(dcm.get("SeriesDescription", "")).lower()
    except Exception:
        pass
    return info

def detect_split_folder(file_path, dataset_root):
    rel_path = os.path.relpath(os.path.dirname(file_path), dataset_root)
    for part in rel_path.split(os.sep):
        if part.lower() in ["train", "test", "val", "validation"]:
            return part
    return None

def classify(info, file_path):
    name = os.path.basename(file_path).lower()
    path = file_path.lower()
    contrast, dose, filter_type, direction = info.values()
    combined = " ".join([contrast, dose, filter_type, direction, name, path])

    if "axial" not in combined:
        return "others"
    if any(x in combined for x in ["contrast", "with_contrast", "non-contrast", "without"]):
        return "contrast"
    if any(x in combined for x in ["lowdose", "low dose", "highdose", "high dose", "kvp"]):
        return "dose"
    if any(x in combined for x in ["bone", "lung", "standard", "parenchyma", "sharp", "smooth"]):
        return "filter"
    return "others"

def is_dicom_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            preamble = f.read(132)
            if len(preamble) >= 132 and preamble[-4:] == b'DICM':
                return True
        try:
            pydicom.dcmread(filepath, stop_before_pixels=True)
            return True
        except Exception:
            return False
    except Exception:
        return False

def arrange_dataset(dataset_name):
    dataset_path = os.path.join(base_path, dataset_name)
    out_dir = os.path.join(arranged_path, dataset_name)
    os.makedirs(out_dir, exist_ok=True)
    counts = defaultdict(int)

    print(f"\n{c.BOLD}{c.INFO}📂 Processing dataset:{c.RESET} {dataset_name}")

    meta_file = None
    for f in os.listdir(dataset_path):
        if f.lower().endswith((".csv", ".xlsx")):
            meta_file = os.path.join(dataset_path, f)
            break

    if meta_file:
        print(f"{c.INFO}ℹ️ Using metadata file:{c.RESET} {os.path.basename(meta_file)}")
        df = pd.read_csv(meta_file) if meta_file.endswith(".csv") else pd.read_excel(meta_file)
        df = df.fillna("")
        if "image_path" not in df.columns:
            print(f"{c.WARN}⚠️ No 'image_path' column found. Metadata skipped.{c.RESET}")
            meta_file = None

    if not meta_file:
        print(f"{c.WARN}⚠️ No metadata found — scanning files...{c.RESET}")
        for root, _, files in os.walk(dataset_path):
            for file in files:
                src_path = os.path.join(root, file)
                if not is_dicom_file(src_path):
                    continue
                info = extract_dicom_info(src_path)
                target_key = classify(info, src_path)
                split_part = detect_split_folder(src_path, dataset_path)
                dst_dir = os.path.join(out_dir, split_part, target_key) if split_part else os.path.join(out_dir, target_key)
                dst_path = os.path.join(dst_dir, file)
                safe_copy(src_path, dst_path)
                counts[target_key] += 1
    else:
        for _, row in df.iterrows():
            image_path = str(row.get("image_path", "")).strip()
            if not image_path or not os.path.exists(image_path):
                continue
            info = {
                "contrast": str(row.get("contrast", "")).lower(),
                "dose": str(row.get("dose", "")).lower(),
                "filter": str(row.get("filter", "")).lower(),
                "direction": str(row.get("direction", "")).lower(),
            }
            target_key = classify(info, image_path)
            split_part = detect_split_folder(image_path, dataset_path)
            dst_dir = os.path.join(out_dir, split_part, target_key) if split_part else os.path.join(out_dir, target_key)
            dst_path = os.path.join(dst_dir, os.path.basename(image_path))
            safe_copy(image_path, dst_path)
            counts[target_key] += 1

    print(f"\n{c.OK}✅ Summary for '{dataset_name}':{c.RESET}")
    for k, v in counts.items():
        print(f"   - {k}: {v} files")
    print(f"{c.OK}✔️ Done arranging {dataset_name}{c.RESET}\n")

datasets = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]

if not datasets:
    print(f"{c.FAIL}[❌] No datasets found in 'Datasets' folder.{c.RESET}")
else:
    print(f"{c.OK}{c.BOLD}[🚀] Found {len(datasets)} dataset(s):{c.RESET} {datasets}\n")
    for ds in datasets:
        arrange_dataset(ds)
