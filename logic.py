
from __future__ import annotations
import math
from typing import Dict, List, Tuple, Any
import pandas as pd

def normalize_text(v) -> str:
    return "" if v is None else str(v).strip()

def safe_int(v):
    if v in ("", None):
        return None
    try:
        f = float(v)
        return int(round(f))
    except Exception:
        return None

def safe_float(v):
    if v in ("", None):
        return None
    try:
        return float(v)
    except Exception:
        return None

def line_type_from_line_no(line_no: str) -> str:
    s = (line_no or "").upper().strip()
    if s.startswith("C2"):
        return "CPT"
    if s.startswith("C1"):
        return "OP"
    if s.startswith("GP"):
        return "GP"
    return ""

def docs_to_frames(parsed_docs: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    header_rows = []
    line_rows = []
    for doc in parsed_docs:
        h = doc["header"]
        header_rows.append({
            "ASN No": h["asn_no"],
            "File Name": h["file_name"],
            "Batch": h["batch"],
            "Sold To": h["sold_to"],
            "Bill To": h["bill_to"],
            "Ship To": h["ship_to"],
            "Location": h["location"],
            "ETA": h["eta"],
            "ETD": h["etd"],
            "ETA Date": h["eta_date"],
            "ETA Time": h["eta_time"],
        })
        for line in doc["lines"]:
            line_rows.append({
                "ASN No": h["asn_no"],
                "Seq": line["seq"],
                "PO No": line["po_no"],
                "Item No": line["item_no"],
                "Rev": str(line["rev"]).zfill(2),
                "Quantity": line["quantity"],
                "Uom": line.get("uom") or "",
                "Net Weight (KG)": line.get("net_weight_kg"),
                "Gross Weight (KG)": line.get("gross_weight_kg"),
                "Packing Spec.": line.get("packing_spec") or "",
                "Lot/MI No./SO No./Invoice No": line.get("lot_mi_so_invoice") or "",
                "SO No": line.get("so_no") or "",
                "Invoice No": line.get("invoice_no") or "",
                "Line No": line.get("line_no") or "",
            })
    headers_df = pd.DataFrame(header_rows)
    lines_df = pd.DataFrame(line_rows)
    if not headers_df.empty:
        headers_df = headers_df.sort_values(["ASN No"]).reset_index(drop=True)
    if not lines_df.empty:
        lines_df = lines_df.sort_values(["ASN No", "Seq"]).reset_index(drop=True)
    return headers_df, lines_df

def build_single_pack_map(df: pd.DataFrame) -> Dict[Tuple[str, str], int]:
    out = {}
    if df is None or df.empty:
        return out
    for _, row in df.iterrows():
        item = normalize_text(row.get("Item"))
        rev = normalize_text(row.get("Rev")).zfill(2) if normalize_text(row.get("Rev")) else ""
        qty = safe_int(row.get("Qty"))
        if item and rev and qty and qty > 0:
            out[(item, rev)] = qty
    return out

def build_pair_map(df: pd.DataFrame) -> Dict[frozenset, Dict[str, Any]]:
    out = {}
    if df is None or df.empty:
        return out
    for _, row in df.iterrows():
        item_a = normalize_text(row.get("Item A"))
        rev_a = normalize_text(row.get("Rev A")).zfill(2) if normalize_text(row.get("Rev A")) else ""
        item_b = normalize_text(row.get("Item B"))
        rev_b = normalize_text(row.get("Rev B")).zfill(2) if normalize_text(row.get("Rev B")) else ""
        qty = safe_int(row.get("Qty"))
        if item_a and rev_a and item_b and rev_b and qty and qty > 0:
            key = frozenset([(item_a, rev_a), (item_b, rev_b)])
            out[key] = {
                "item_a": item_a, "rev_a": rev_a,
                "item_b": item_b, "rev_b": rev_b,
                "qty": qty,
            }
    return out

def consolidate_for_review(raw_lines_df: pd.DataFrame, single_pack_df: pd.DataFrame | None, pair_df: pd.DataFrame | None) -> pd.DataFrame:
    if raw_lines_df is None or raw_lines_df.empty:
        cols = ["ASN No","PO No","Item No","Rev","Quantity","Uom","Net Weight (KG)","SO No","Invoice No","Line No",
                "Packing Size","Full Cartons","Loose Qty","Total Cartons","Note"]
        return pd.DataFrame(columns=cols)

    grouped_rows = []
    grouped = raw_lines_df.groupby(["ASN No", "Item No", "Rev"], dropna=False, sort=False)
    for (asn, item, rev), g in grouped:
        quantity = pd.to_numeric(g["Quantity"], errors="coerce").fillna(0).sum()
        net_weight = pd.to_numeric(g["Net Weight (KG)"], errors="coerce").fillna(0).sum()
        line_nos = [normalize_text(v) for v in g["Line No"].tolist() if normalize_text(v)]
        grouped_rows.append({
            "ASN No": normalize_text(asn),
            "PO No": ", ".join(dict.fromkeys([normalize_text(v) for v in g["PO No"].tolist() if normalize_text(v)])),
            "Item No": normalize_text(item),
            "Rev": normalize_text(rev).zfill(2),
            "Quantity": int(round(quantity)) if abs(quantity - round(quantity)) < 1e-9 else quantity,
            "Uom": normalize_text(g["Uom"].iloc[0]),
            "Net Weight (KG)": round(net_weight, 5) if net_weight else None,
            "SO No": ", ".join(dict.fromkeys([normalize_text(v) for v in g["SO No"].tolist() if normalize_text(v)])),
            "Invoice No": ", ".join(dict.fromkeys([normalize_text(v) for v in g["Invoice No"].tolist() if normalize_text(v)])),
            "Line No": ", ".join(dict.fromkeys(line_nos)),
            "Packing Size": None,
            "Full Cartons": None,
            "Loose Qty": None,
            "Total Cartons": None,
            "Note": "",
            "_Line Type": line_type_from_line_no(line_nos[0] if line_nos else ""),
            "_Calc": "Single",
        })

    df = pd.DataFrame(grouped_rows)
    if df.empty:
        return df

    single_pack = build_single_pack_map(single_pack_df)
    pair_map = build_pair_map(pair_df)

    # Base single calculation by Item + Rev
    for idx in df.index:
        item = normalize_text(df.at[idx, "Item No"])
        rev = normalize_text(df.at[idx, "Rev"]).zfill(2)
        qty = safe_float(df.at[idx, "Quantity"]) or 0
        pack = single_pack.get((item, rev))
        if pack:
            df.at[idx, "Packing Size"] = pack
            full = int(qty // pack)
            loose = int(qty % pack)
            total = full + (1 if loose > 0 else 0)
            df.at[idx, "Full Cartons"] = full
            df.at[idx, "Loose Qty"] = loose
            df.at[idx, "Total Cartons"] = total
            df.at[idx, "Note"] = ""
        else:
            df.at[idx, "Note"] = "No Packing"

    # Pair logic per ASN
    for asn, g in df.groupby("ASN No", sort=False):
        idx_lookup = {(normalize_text(df.at[idx, "Item No"]), normalize_text(df.at[idx, "Rev"]).zfill(2)): idx for idx in g.index}
        processed = set()
        for key, meta in pair_map.items():
            a = (meta["item_a"], meta["rev_a"])
            b = (meta["item_b"], meta["rev_b"])
            if a in idx_lookup and b in idx_lookup:
                idx_a = idx_lookup[a]
                idx_b = idx_lookup[b]
                if idx_a in processed or idx_b in processed:
                    continue
                qty_a = safe_float(df.at[idx_a, "Quantity"]) or 0
                qty_b = safe_float(df.at[idx_b, "Quantity"]) or 0
                pair_qty = meta["qty"]
                pair_units = (qty_a + qty_b) / 2.0
                full = int(pair_units // pair_qty)
                loose = pair_units % pair_qty
                loose_display = int(loose) if abs(loose - round(loose)) < 1e-9 else round(loose, 4)
                total = full + (1 if loose > 0 else 0)
                for idx in [idx_a, idx_b]:
                    df.at[idx, "Packing Size"] = pair_qty
                    df.at[idx, "Full Cartons"] = full
                    df.at[idx, "Loose Qty"] = loose_display
                    df.at[idx, "Total Cartons"] = total
                    df.at[idx, "_Calc"] = "Pair"
                    if normalize_text(df.at[idx, "Note"]) == "No Packing":
                        df.at[idx, "Note"] = ""
                processed.add(idx_a)
                processed.add(idx_b)

    visible_cols = ["ASN No","PO No","Item No","Rev","Quantity","Uom","Net Weight (KG)","SO No","Invoice No","Line No",
                    "Packing Size","Full Cartons","Loose Qty","Total Cartons","Note"]
    return df[visible_cols + ["_Line Type", "_Calc"]]

def recalc_from_review(edited_df: pd.DataFrame, single_pack_df: pd.DataFrame | None, pair_df: pd.DataFrame | None) -> pd.DataFrame:
    if edited_df is None or edited_df.empty:
        return edited_df

    df = edited_df.copy()
    single_pack = build_single_pack_map(single_pack_df)
    pair_map = build_pair_map(pair_df)

    if "_Line Type" not in df.columns:
        df["_Line Type"] = df["Line No"].map(line_type_from_line_no)
    if "_Calc" not in df.columns:
        df["_Calc"] = "Single"

    # Recompute line type from current line no
    df["_Line Type"] = df["Line No"].fillna("").map(line_type_from_line_no)
    df["_Calc"] = "Single"

    for idx in df.index:
        item = normalize_text(df.at[idx, "Item No"])
        rev = normalize_text(df.at[idx, "Rev"]).zfill(2)
        df.at[idx, "Rev"] = rev
        qty = safe_float(df.at[idx, "Quantity"]) or 0
        pack = safe_int(df.at[idx, "Packing Size"])
        master_pack = single_pack.get((item, rev))
        effective_pack = pack if pack and pack > 0 else master_pack
        if effective_pack:
            df.at[idx, "Packing Size"] = effective_pack
            full = int(qty // effective_pack)
            loose = qty % effective_pack
            loose_display = int(loose) if abs(loose - round(loose)) < 1e-9 else round(loose, 4)
            total = full + (1 if loose > 0 else 0)
            df.at[idx, "Full Cartons"] = full
            df.at[idx, "Loose Qty"] = loose_display
            df.at[idx, "Total Cartons"] = total
            if normalize_text(df.at[idx, "Note"]) == "No Packing":
                df.at[idx, "Note"] = ""
        else:
            df.at[idx, "Packing Size"] = None
            df.at[idx, "Full Cartons"] = None
            df.at[idx, "Loose Qty"] = None
            df.at[idx, "Total Cartons"] = None
            df.at[idx, "Note"] = "No Packing"

    # Pair override per ASN
    for asn, g in df.groupby("ASN No", sort=False):
        idx_lookup = {(normalize_text(df.at[idx, "Item No"]), normalize_text(df.at[idx, "Rev"]).zfill(2)): idx for idx in g.index}
        processed = set()
        for key, meta in pair_map.items():
            a = (meta["item_a"], meta["rev_a"])
            b = (meta["item_b"], meta["rev_b"])
            if a in idx_lookup and b in idx_lookup:
                idx_a = idx_lookup[a]
                idx_b = idx_lookup[b]
                if idx_a in processed or idx_b in processed:
                    continue
                qty_a = safe_float(df.at[idx_a, "Quantity"]) or 0
                qty_b = safe_float(df.at[idx_b, "Quantity"]) or 0
                pair_qty = meta["qty"]
                pair_units = (qty_a + qty_b) / 2.0
                full = int(pair_units // pair_qty)
                loose = pair_units % pair_qty
                loose_display = int(loose) if abs(loose - round(loose)) < 1e-9 else round(loose, 4)
                total = full + (1 if loose > 0 else 0)
                for idx in [idx_a, idx_b]:
                    df.at[idx, "Packing Size"] = pair_qty
                    df.at[idx, "Full Cartons"] = full
                    df.at[idx, "Loose Qty"] = loose_display
                    df.at[idx, "Total Cartons"] = total
                    df.at[idx, "_Calc"] = "Pair"
                    if normalize_text(df.at[idx, "Note"]) == "No Packing":
                        df.at[idx, "Note"] = ""
                processed.add(idx_a)
                processed.add(idx_b)
    return df

def build_header_export(headers_df: pd.DataFrame, review_df: pd.DataFrame) -> pd.DataFrame:
    if headers_df is None or headers_df.empty:
        return pd.DataFrame(columns=["No.","ASN No","Batch","Sold to","Bill To","Ship To","Location","ETA","ETD","Line No"])
    rows = []
    asn_to_line = {}
    if review_df is not None and not review_df.empty:
        temp = review_df.groupby("ASN No", sort=False)["Line No"].first().to_dict()
        asn_to_line = {k: normalize_text(v) for k, v in temp.items()}
    for i, (_, h) in enumerate(headers_df.sort_values(["ASN No"]).iterrows(), start=1):
        rows.append({
            "No.": i,
            "ASN No": h["ASN No"],
            "Batch": h["Batch"],
            "Sold to": h["Sold To"],
            "Bill To": h["Bill To"],
            "Ship To": h["Ship To"],
            "Location": h["Location"],
            "ETA": h["ETA"],
            "ETD": h["ETD"],
            "Line No": asn_to_line.get(h["ASN No"], ""),
        })
    return pd.DataFrame(rows)

def compute_summary(review_df: pd.DataFrame, headers_df: pd.DataFrame) -> Dict[str, Any]:
    review_df = review_df.copy() if review_df is not None else pd.DataFrame()
    out = {
        "total_asn": 0,
        "cpt": 0,
        "op": 0,
        "gp": 0,
        "unique_items": 0,
        "total_qty": 0,
        "total_cartons": 0,
        "missing_packing": 0,
    }
    if headers_df is not None and not headers_df.empty:
        out["total_asn"] = headers_df["ASN No"].nunique()
    if review_df is None or review_df.empty:
        return out

    review_df["_Line Type"] = review_df.get("_Line Type", review_df["Line No"].fillna("").map(line_type_from_line_no))
    for asn, g in review_df.groupby("ASN No"):
        types = set(g["_Line Type"].dropna().tolist())
        if "CPT" in types:
            out["cpt"] += 1
        if "OP" in types:
            out["op"] += 1
        if "GP" in types:
            out["gp"] += 1

    out["unique_items"] = review_df[["Item No", "Rev"]].drop_duplicates().shape[0]
    out["total_qty"] = int(pd.to_numeric(review_df["Quantity"], errors="coerce").fillna(0).sum())
    out["total_cartons"] = pd.to_numeric(review_df["Total Cartons"], errors="coerce").fillna(0).sum()
    out["missing_packing"] = int((review_df["Note"].fillna("") == "No Packing").sum())
    return out

def earliest_eta(headers_df: pd.DataFrame) -> str:
    if headers_df is None or headers_df.empty or "ETA" not in headers_df.columns:
        return ""
    vals = [normalize_text(v) for v in headers_df["ETA"].tolist() if normalize_text(v)]
    if not vals:
        return ""
    def key(v):
        # expected format YYYY-MM-DD HH:MM
        return v
    return min(vals, key=key)
