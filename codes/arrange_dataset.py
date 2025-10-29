import os
import shutil
import pandas as pd
import pydicom
import re
from collections import defaultdict

base_path = os.path.abspath("Datasets")
arranged_path = os.path.abspath("Arranged_datasets")
os.makedirs(arranged_path, exist_ok=True)

categories = ["contrast", "dose", "filter", "direction", "others"]

def safe_copy(src, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, os.path.basename(src))
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
    return dst

def is_dicom(path):
    try:
        with open(path, 'rb') as f:
            if f.read(132)[-4:] == b'DICM':
                return True
        pydicom.dcmread(path, stop_before_pixels=True)
        return True
    except:
        return False

def extract_info(path):
    info = {"contrast": "", "dose": "", "filter": "", "direction": ""}
    try:
        dcm = pydicom.dcmread(path, stop_before_pixels=True)
        info["contrast"] = str(dcm.get("ContrastBolusAgent", "")).lower()
        info["dose"] = str(dcm.get("KVP", "")).lower()
        info["filter"] = str(dcm.get("ConvolutionKernel", "")).lower()
        info["direction"] = str(dcm.get("SeriesDescription", "")).lower()
        fname = os.path.basename(path).lower()
        if info["direction"] == "":
            m = re.search(r"(axial|coronal|sagittal|3d)", fname)
            if m:
                info["direction"] = m.group(1)
    except:
        pass
    return info

def classify(info, filename):
    fname = filename.lower()
    # بررسی چهار شاخه اصلی
    if re.search(r"(contrast|non[- ]?contrast|with|without)", f"{info['contrast']} {fname}"):
        return "contrast"
    elif re.search(r"(low[- ]?dose|high[- ]?dose)", f"{info['dose']} {fname}"):
        return "dose"
    elif re.search(r"(bone|lung|standard|sharp|smooth|kernel)", f"{info['filter']} {fname}"):
        return "filter"
    elif re.search(r"(axial|coronal|sagittal|3d)", f"{info['direction']} {fname}"):
        return "direction"
    else:
        return "others"

def arrange_dataset(dataset_name):
    dataset_dir = os.path.join(base_path, dataset_name)
    output_dir = os.path.join(arranged_path, dataset_name)
    os.makedirs(output_dir, exist_ok=True)

    # ایجاد شاخه‌های اصلی
    for cat in categories:
        os.makedirs(os.path.join(output_dir, cat), exist_ok=True)

    rows = []
    counts = defaultdict(int)
    total_files = 0

    for root, _, files in os.walk(dataset_dir):
        for f in files:
            src = os.path.join(root, f)
            if not is_dicom(src):
                continue

            total_files += 1
            info = extract_info(src)
            category = classify(info, f)
            dst_dir = os.path.join(output_dir, category)
            dst = safe_copy(src, dst_dir)

            rows.append({
                "dataset": dataset_name,
                "contrast": info["contrast"],
                "dose": info["dose"],
                "filter": info["filter"],
                "direction": info["direction"],
                "category": category,
                "source_path": os.path.relpath(src, base_path),
                "dest_path": os.path.relpath(dst, arranged_path)
            })
            counts[category] += 1

    df = pd.DataFrame(rows)
    csv_path = os.path.join(output_dir, f"report_{dataset_name}.csv")
    df.to_csv(csv_path, index=False)

    print(f"\n✅ Dataset '{dataset_name}' done. Total DICOM files: {total_files}")
    for k in categories:
        print(f"   {k}: {counts[k]}")
    print(f"Report saved → {csv_path}\n")

# اجرای روی تمام دیتاست‌ها
datasets = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
if not datasets:
    print("❌ No datasets found.")
else:
    for ds in datasets:
        arrange_dataset(ds)
