
import re
from io import BytesIO
from typing import List, Dict, Any
from pypdf import PdfReader

def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages)

def norm(s: str) -> str:
    return re.sub(r'[ \t]+', ' ', (s or '')).strip()

def clean_multiline_value(s: str) -> str:
    s = re.sub(r'\s*\n\s*', ' ', s or '')
    s = re.sub(r'[ \t]+', ' ', s)
    return s.strip()

def parse_header(text: str, filename: str) -> Dict[str, Any]:
    m = re.search(r'LIMITED\(12350\)\s*B\s*([A-Z0-9-]+)\s+Delivery Note', text, re.I | re.S)
    batch = norm(m.group(1)) if m else ""

    asn = re.search(r'ASN No\s*:?\s*([A-Z0-9-]+)', text, re.I)
    sold_to = re.search(r'Sold To:\s*(.*?)\s*ASN No\s*:?', text, re.I | re.S)
    bill_to = re.search(r'Bill To:\s*(.*?)\s*Ship To:', text, re.I | re.S)
    ship_eta = re.search(r'Ship To:\s*(.*?)\s*ETA\s*:?\s*([0-9:\- ]+)', text, re.I | re.S)
    location = re.search(r'Location:\s*(.*?)\s*ETD\s*:', text, re.I | re.S)
    etd = re.search(r'ETD\s*:?\s*(.*?)\s*(?:Issued By|Seq PO No\.)', text, re.I | re.S)

    eta_raw = norm(ship_eta.group(2)) if ship_eta else ""
    eta_date = ""
    eta_time = ""
    m_eta = re.match(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', eta_raw)
    if m_eta:
        eta_date = m_eta.group(1)
        eta_time = m_eta.group(2)

    return {
        "file_name": filename,
        "asn_no": norm(asn.group(1)) if asn else "",
        "batch": batch,
        "sold_to": clean_multiline_value(sold_to.group(1)) if sold_to else "",
        "bill_to": clean_multiline_value(bill_to.group(1)) if bill_to else "",
        "ship_to": clean_multiline_value(ship_eta.group(1)) if ship_eta else "",
        "location": clean_multiline_value(location.group(1)) if location else "",
        "eta": eta_raw,
        "eta_date": eta_date,
        "eta_time": eta_time,
        "etd": clean_multiline_value(etd.group(1)) if etd else "",
    }

def _split_row_blocks(text: str) -> List[str]:
    blocks = []
    for m in re.finditer(r'(?m)^\s*(\d+)\s+', text):
        start = m.start()
        nxt = re.search(r'(?m)^\s*\d+\s+', text[m.end():])
        end = len(text) if not nxt else m.end() + nxt.start()
        blocks.append(text[start:end])
    return blocks

def _parse_row_block(block: str, asn_no: str) -> Dict[str, Any] | None:
    compact = re.sub(r'[ \t]+', ' ', block).strip()
    m = re.match(r'(\d+)\s+([A-Z0-9-]+)\s+(\d+)\s+([A-Z0-9]+)\s+([0-9.]+)\s+([A-Z]+)\s*(.*)$', compact, re.S)
    if not m:
        return None
    seq, po_no, item_no, rev, qty, uom, rest = m.groups()
    rest = rest.strip()

    net_weight = None
    m_num = re.match(r'([0-9.]+)\s+(.*)$', rest, re.S)
    if m_num:
        net_weight = float(m_num.group(1))
        rest = m_num.group(2).strip()

    so_no = ""
    m_so = re.search(r'So:\s*([0-9]+)', rest, re.I)
    if m_so:
        so_no = m_so.group(1)

    invoice_no = ""
    m_inv = re.search(r'\b(XC[0-9]+)\b', rest, re.I)
    if m_inv:
        invoice_no = m_inv.group(1)

    line_no = ""
    m_line = re.search(r'\b(C[12])\s*-\s*([0-9]+[A-Z]?)', rest, re.I)
    if m_line:
        line_no = f"{m_line.group(1).upper()}-{m_line.group(2).upper()}"
    elif re.search(r'\bGP\s*JOB\b', rest, re.I):
        line_no = "GP JOB"
    else:
        m_gp = re.search(r'\bGP\b.*$', rest, re.I)
        if m_gp:
            line_no = "GP"

    lot = ""
    if so_no and invoice_no:
        lot = f"So: {so_no} {invoice_no}"
    elif invoice_no:
        lot = invoice_no
    elif so_no:
        lot = f"So: {so_no}"

    return {
        "asn_no": asn_no,
        "seq": int(seq),
        "po_no": po_no,
        "item_no": item_no,
        "rev": rev,
        "quantity": float(qty) if "." in qty else int(qty),
        "uom": uom,
        "net_weight_kg": net_weight,
        "gross_weight_kg": None,
        "packing_spec": "",
        "lot_mi_so_invoice": lot,
        "so_no": so_no,
        "invoice_no": invoice_no,
        "line_no": line_no,
    }

def parse_lines(text: str, asn_no: str) -> List[Dict[str, Any]]:
    sections = re.findall(r'Line\s*\n?No\.\s*(.*?)\s*Total Quantity\s*([0-9.]+)', text, re.I | re.S)
    lines: List[Dict[str, Any]] = []
    for section, _total in sections:
        for block in _split_row_blocks(section):
            row = _parse_row_block(block, asn_no)
            if row:
                lines.append(row)
    lines.sort(key=lambda x: x["seq"])
    return lines

def parse_delivery_note(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    text = extract_text_from_pdf(file_bytes)
    header = parse_header(text, filename)
    lines = parse_lines(text, header["asn_no"])
    header["line_count"] = len(lines)
    header["total_quantity"] = sum(float(x["quantity"]) for x in lines)
    return {"header": header, "lines": lines, "raw_text": text}

def parse_multiple(files: List[tuple[str, bytes]]) -> List[Dict[str, Any]]:
    parsed = [parse_delivery_note(file_bytes, filename) for filename, file_bytes in files]
    parsed.sort(key=lambda d: d["header"]["asn_no"])
    return parsed
