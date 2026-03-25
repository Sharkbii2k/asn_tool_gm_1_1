from __future__ import annotations
import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from parser import parse_multiple
from logic import docs_to_frames, consolidate_for_review, recalc_from_review, compute_summary, earliest_eta
from storage import load_single_df, load_pair_df, save_single_df, save_pair_df, import_single, import_pair
from workbook_builder import build_workbook_bytes

APP_DIR = Path(__file__).resolve().parent
SESSION_PATH = APP_DIR / "data" / "ui_session.json"

app = FastAPI(title="ASN Tool GM 2.0")
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    out = []
    for rec in df.to_dict(orient="records"):
        fixed = {}
        for k, v in rec.items():
            fixed[k] = None if pd.isna(v) else v
        out.append(fixed)
    return out

def _save_ui_session(headers_df: pd.DataFrame, raw_lines_df: pd.DataFrame, review_df: pd.DataFrame):
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "headers": _records(headers_df),
        "raw_lines": _records(raw_lines_df),
        "review_rows": _records(review_df),
    }
    SESSION_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

def _load_ui_session():
    if not SESSION_PATH.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    payload = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
    return (
        pd.DataFrame(payload.get("headers", [])),
        pd.DataFrame(payload.get("raw_lines", [])),
        pd.DataFrame(payload.get("review_rows", [])),
    )

@app.get("/")
def index():
    return FileResponse(APP_DIR / "static" / "index.html")

@app.get("/manifest.json")
def manifest():
    return FileResponse(APP_DIR / "static" / "manifest.json", media_type="application/manifest+json")

@app.get("/api/state")
def state():
    headers_df, raw_lines_df, review_df = _load_ui_session()
    return JSONResponse({
        "headers": _records(headers_df),
        "raw_lines": _records(raw_lines_df),
        "review_rows": _records(review_df),
        "summary": compute_summary(review_df, headers_df),
        "earliest_eta": earliest_eta(headers_df),
        "single_packing": _records(load_single_df()),
        "pair_packing": _records(load_pair_df()),
    })

@app.post("/api/parse")
async def api_parse(files: list[UploadFile] = File(...)):
    payload = []
    for f in files:
        if (f.filename or "").lower().endswith(".pdf"):
            payload.append((f.filename, await f.read()))
    if not payload:
        raise HTTPException(status_code=400, detail="Hiện bản này chỉ hỗ trợ PDF gốc text-selectable.")
    parsed = parse_multiple(payload)
    headers_df, raw_lines_df = docs_to_frames(parsed)
    review_df = consolidate_for_review(raw_lines_df, load_single_df(), load_pair_df())
    _save_ui_session(headers_df, raw_lines_df, review_df)
    return JSONResponse({
        "headers": _records(headers_df),
        "raw_lines": _records(raw_lines_df),
        "review_rows": _records(review_df),
        "summary": compute_summary(review_df, headers_df),
        "earliest_eta": earliest_eta(headers_df),
    })

@app.post("/api/recalculate")
async def api_recalculate(payload: dict[str, Any]):
    headers_df = pd.DataFrame(payload.get("headers", []))
    raw_lines_df = pd.DataFrame(payload.get("raw_lines", []))
    review_df = pd.DataFrame(payload.get("review_rows", []))
    recalculated = recalc_from_review(review_df, load_single_df(), load_pair_df())
    _save_ui_session(headers_df, raw_lines_df, recalculated)
    return JSONResponse({
        "review_rows": _records(recalculated),
        "summary": compute_summary(recalculated, headers_df),
    })

@app.post("/api/export")
async def api_export(payload: dict[str, Any] | None = None):
    if payload:
        headers_df = pd.DataFrame(payload.get("headers", []))
        raw_lines_df = pd.DataFrame(payload.get("raw_lines", []))
        review_df = pd.DataFrame(payload.get("review_rows", []))
        if not headers_df.empty and not review_df.empty:
            _save_ui_session(headers_df, raw_lines_df, review_df)
    headers_df, raw_lines_df, review_df = _load_ui_session()
    if headers_df.empty or review_df.empty:
        raise HTTPException(status_code=400, detail="No data to export.")
    wb = build_workbook_bytes(headers_df, raw_lines_df, review_df)
    eta = earliest_eta(headers_df)
    fname = f"ASN_{eta[:10]}.xlsx" if eta else "ASN_export.xlsx"
    return StreamingResponse(BytesIO(wb),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'})

@app.get("/api/export")
def api_export_get():
    headers_df, raw_lines_df, review_df = _load_ui_session()
    if headers_df.empty or review_df.empty:
        raise HTTPException(status_code=400, detail="No data to export.")
    wb = build_workbook_bytes(headers_df, raw_lines_df, review_df)
    eta = earliest_eta(headers_df)
    fname = f"ASN_{eta[:10]}.xlsx" if eta else "ASN_export.xlsx"
    return StreamingResponse(BytesIO(wb),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'})

@app.get("/api/packing/single")
def get_single():
    return {"rows": _records(load_single_df())}

@app.post("/api/packing/single/save")
async def save_single(payload: dict[str, Any]):
    df = pd.DataFrame(payload.get("rows", []))
    save_single_df(df)
    return {"ok": True, "rows": _records(load_single_df())}

@app.post("/api/packing/single/import")
async def upload_single(file: UploadFile = File(...), mode: str = Form("append")):
    rows = import_single(await file.read(), file.filename, mode=mode)
    return {"ok": True, "rows": _records(rows)}

@app.get("/api/packing/pair")
def get_pair():
    return {"rows": _records(load_pair_df())}

@app.post("/api/packing/pair/save")
async def save_pair(payload: dict[str, Any]):
    df = pd.DataFrame(payload.get("rows", []))
    save_pair_df(df)
    return {"ok": True, "rows": _records(load_pair_df())}

@app.post("/api/packing/pair/import")
async def upload_pair(file: UploadFile = File(...), mode: str = Form("append")):
    rows = import_pair(await file.read(), file.filename, mode=mode)
    return {"ok": True, "rows": _records(rows)}
