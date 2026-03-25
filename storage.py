
from __future__ import annotations
from pathlib import Path
from io import BytesIO
import os
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

SINGLE_PATH = DATA_DIR / "packing_master.xlsx"
PAIR_PATH = DATA_DIR / "pair_master.xlsx"

SINGLE_COLS = ["Item", "Rev", "Qty"]
PAIR_COLS = ["Item A", "Rev A", "Item B", "Rev B", "Qty"]

def _read_upload(upload_bytes: bytes, filename: str) -> pd.DataFrame:
    ext = os.path.splitext(filename.lower())[1]
    if ext == ".csv":
        return pd.read_csv(BytesIO(upload_bytes))
    return pd.read_excel(BytesIO(upload_bytes))

def ensure_files():
    if not SINGLE_PATH.exists():
        pd.DataFrame(columns=SINGLE_COLS).to_excel(SINGLE_PATH, index=False)
    if not PAIR_PATH.exists():
        pd.DataFrame(columns=PAIR_COLS).to_excel(PAIR_PATH, index=False)

def load_single_df() -> pd.DataFrame:
    ensure_files()
    df = pd.read_excel(SINGLE_PATH)
    for col in SINGLE_COLS:
        if col not in df.columns:
            df[col] = ""
    return df[SINGLE_COLS].fillna("")

def load_pair_df() -> pd.DataFrame:
    ensure_files()
    df = pd.read_excel(PAIR_PATH)
    for col in PAIR_COLS:
        if col not in df.columns:
            df[col] = ""
    return df[PAIR_COLS].fillna("")

def save_single_df(df: pd.DataFrame):
    df = df.copy()
    for col in SINGLE_COLS:
        if col not in df.columns:
            df[col] = ""
    df = df[SINGLE_COLS].fillna("")
    df.to_excel(SINGLE_PATH, index=False)

def save_pair_df(df: pd.DataFrame):
    df = df.copy()
    for col in PAIR_COLS:
        if col not in df.columns:
            df[col] = ""
    df = df[PAIR_COLS].fillna("")
    df.to_excel(PAIR_PATH, index=False)

def import_single(upload_bytes: bytes, filename: str, mode: str = "append") -> pd.DataFrame:
    df = _read_upload(upload_bytes, filename)
    rename = {c: c.strip() for c in df.columns}
    df = df.rename(columns=rename)
    cols = {"Item": None, "Rev": None, "Qty": None}
    for c in df.columns:
        low = c.strip().lower().replace("_"," ").replace(".","")
        if low == "item":
            cols["Item"] = c
        elif low == "rev":
            cols["Rev"] = c
        elif low in ("qty","quantity"):
            cols["Qty"] = c
    out = pd.DataFrame({
        "Item": df[cols["Item"]] if cols["Item"] else "",
        "Rev": df[cols["Rev"]] if cols["Rev"] else "",
        "Qty": df[cols["Qty"]] if cols["Qty"] else "",
    }).fillna("")
    base = load_single_df()
    merged = out if mode == "replace" else pd.concat([base, out], ignore_index=True)
    merged["Rev"] = merged["Rev"].astype(str).str.zfill(2)
    merged = merged[merged["Item"].astype(str).str.strip() != ""]
    merged = merged.drop_duplicates(subset=["Item","Rev"], keep="last").sort_values(["Item","Rev"]).reset_index(drop=True)
    save_single_df(merged)
    return merged

def import_pair(upload_bytes: bytes, filename: str, mode: str = "append") -> pd.DataFrame:
    df = _read_upload(upload_bytes, filename)
    rename = {c: c.strip() for c in df.columns}
    df = df.rename(columns=rename)
    cols = {"Item A": None, "Rev A": None, "Item B": None, "Rev B": None, "Qty": None}
    for c in df.columns:
        low = c.strip().lower().replace("_"," ").replace(".","")
        if low == "item a":
            cols["Item A"] = c
        elif low == "rev a":
            cols["Rev A"] = c
        elif low == "item b":
            cols["Item B"] = c
        elif low == "rev b":
            cols["Rev B"] = c
        elif low in ("qty","quantity"):
            cols["Qty"] = c
    out = pd.DataFrame({
        "Item A": df[cols["Item A"]] if cols["Item A"] else "",
        "Rev A": df[cols["Rev A"]] if cols["Rev A"] else "",
        "Item B": df[cols["Item B"]] if cols["Item B"] else "",
        "Rev B": df[cols["Rev B"]] if cols["Rev B"] else "",
        "Qty": df[cols["Qty"]] if cols["Qty"] else "",
    }).fillna("")
    base = load_pair_df()
    merged = out if mode == "replace" else pd.concat([base, out], ignore_index=True)
    merged["Rev A"] = merged["Rev A"].astype(str).str.zfill(2)
    merged["Rev B"] = merged["Rev B"].astype(str).str.zfill(2)
    merged = merged[(merged["Item A"].astype(str).str.strip() != "") & (merged["Item B"].astype(str).str.strip() != "")]
    merged = merged.drop_duplicates(subset=["Item A","Rev A","Item B","Rev B"], keep="last").sort_values(["Item A","Rev A","Item B","Rev B"]).reset_index(drop=True)
    save_pair_df(merged)
    return merged
