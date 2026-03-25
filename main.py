
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
from logic import (
    docs_to_frames,
    consolidate_for_review,
    recalc_from_review,
    compute_summary,
    earliest_eta,
)
from storage import (
    load_single_df,
    load_pair_df,
    save_single_df,
    save_pair_df,
    import_single,
    import_pair,
)
from workbook_builder import build_workbook_bytes

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="ASN Tool GM 1.1")
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    out = []
    for rec in df.to_dict(orient="records"):
        fixed = {}
        for k, v in rec.items():
            if pd.isna(v):
                fixed[k] = None
            else:
                fixed[k] = v
        out.append(fixed)
    return out


@app.get("/")
def index():
    return FileResponse(APP_DIR / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True, "app": "ASN Tool GM 1.1"}


@app.post("/api/parse")
async def api_parse(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    payload = []
    for f in files:
        payload.append((f.filename, await f.read()))
    parsed = parse_multiple(payload)
    headers_df, raw_lines_df = docs_to_frames(parsed)
    review_df = consolidate_for_review(raw_lines_df, load_single_df(), load_pair_df())
    return JSONResponse({
        "headers": _records(headers_df),
        "raw_lines": _records(raw_lines_df),
        "review_rows": _records(review_df),
        "summary": compute_summary(review_df, headers_df),
        "earliest_eta": earliest_eta(headers_df),
    })


@app.post("/api/recalculate")
async def api_recalculate(payload: dict[str, Any]):
    review_rows = payload.get("review_rows", [])
    headers = payload.get("headers", [])
    review_df = pd.DataFrame(review_rows)
    headers_df = pd.DataFrame(headers)
    recalculated = recalc_from_review(review_df, load_single_df(), load_pair_df())
    return JSONResponse({
        "review_rows": _records(recalculated),
        "summary": compute_summary(recalculated, headers_df),
    })


@app.post("/api/export")
async def api_export(payload: dict[str, Any]):
    headers_df = pd.DataFrame(payload.get("headers", []))
    raw_lines_df = pd.DataFrame(payload.get("raw_lines", []))
    review_df = pd.DataFrame(payload.get("review_rows", []))
    if headers_df.empty or review_df.empty:
        raise HTTPException(status_code=400, detail="No data to export.")
    wb = build_workbook_bytes(headers_df, raw_lines_df, review_df)
    eta = earliest_eta(headers_df)
    fname = f"ASN_{eta[:10]}.xlsx" if eta else "ASN_export.xlsx"
    return StreamingResponse(
        BytesIO(wb),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )


@app.get("/api/packing/single")
def get_single():
    df = load_single_df()
    return {"rows": _records(df)}


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
    df = load_pair_df()
    return {"rows": _records(df)}


@app.post("/api/packing/pair/save")
async def save_pair(payload: dict[str, Any]):
    df = pd.DataFrame(payload.get("rows", []))
    save_pair_df(df)
    return {"ok": True, "rows": _records(load_pair_df())}


@app.post("/api/packing/pair/import")
async def upload_pair(file: UploadFile = File(...), mode: str = Form("append")):
    rows = import_pair(await file.read(), file.filename, mode=mode)
    return {"ok": True, "rows": _records(rows)}
