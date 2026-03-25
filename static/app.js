
const state = { files: [], headers: [], rawLines: [], reviewRows: [], earliestEta: '', singlePacking: [], pairPacking: [] };
const tabs = document.querySelectorAll('.tab');
const panels = document.querySelectorAll('.tab-panel');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
const scanBtn = document.getElementById('scanBtn');
const scanStatus = document.getElementById('scanStatus');
const headerBody = document.getElementById('headerPreviewBody');
const headerCountBadge = document.getElementById('headerCountBadge');
const resultTableBody = document.querySelector('#resultTable tbody');
const cartonSummary = document.getElementById('cartonSummary');
const etaBadge = document.getElementById('etaBadge');
const summaryBadge = document.getElementById('summaryBadge');
const packingBody = document.querySelector('#packingTable tbody');
const pairBody = document.querySelector('#pairTable tbody');

function qs(id){ return document.getElementById(id); }
function esc(v){ return v === null || v === undefined ? '' : String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;'); }
function toNumberOrText(v){ if (v === '') return ''; const num = Number(v); return Number.isNaN(num) ? v : num; }

tabs.forEach(tab => tab.addEventListener('click', () => {
  const target = tab.dataset.tab;
  tabs.forEach(t => t.classList.remove('active'));
  panels.forEach(p => p.classList.remove('active'));
  tab.classList.add('active');
  document.getElementById(`tab-${target}`).classList.add('active');
}));

document.querySelectorAll('.packing-subtab').forEach(btn => btn.addEventListener('click', () => {
  const target = btn.dataset.pack;
  document.querySelectorAll('.packing-subtab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.packing-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(`pack-${target}`).classList.add('active');
}));

function setStatus(text, type='muted'){ scanStatus.textContent = text; scanStatus.className = `status-box ${type}`; }

fileInput?.addEventListener('change', () => {
  state.files = Array.from(fileInput.files || []);
  if (!state.files.length) { fileList.textContent = 'Chưa có file nào được chọn.'; fileList.classList.add('empty'); return; }
  fileList.classList.remove('empty');
  fileList.innerHTML = state.files.map((f, i) => `${i + 1}. ${f.name}`).join('<br>');
});

function renderHeaders(){
  headerBody.innerHTML = '';
  headerCountBadge.textContent = `${state.headers.length} ASN`;
  if (!state.headers.length) { headerBody.innerHTML = `<tr><td colspan="5">Chưa có dữ liệu.</td></tr>`; return; }
  state.headers.forEach(r => headerBody.insertAdjacentHTML('beforeend', `<tr><td>${esc(r["ASN No"])}</td><td>${esc(r["ETA"])}</td><td>${esc(r["ETD"] || '-')}</td><td>${esc(r["Sold To"])}</td><td>${esc(r["Bill To"])}</td></tr>`));
}

function noteClass(note){
  if ((note || '') === 'No Packing') return 'warn-note';
  if ((note || '') === 'Packing Conflict') return 'conflict-note';
  return 'ok-note';
}

function renderResultTable(){
  resultTableBody.innerHTML = '';
  if (!state.reviewRows.length) { resultTableBody.innerHTML = `<tr><td colspan="15">Chưa có dữ liệu.</td></tr>`; return; }
  state.reviewRows.forEach((r, idx) => {
    resultTableBody.insertAdjacentHTML('beforeend', `
      <tr data-idx="${idx}">
        <td contenteditable="true">${esc(r["ASN No"] || '')}</td>
        <td contenteditable="true">${esc(r["PO No"] || '')}</td>
        <td contenteditable="true">${esc(r["Item No"] || '')}</td>
        <td contenteditable="true">${esc(r["Rev"] || '')}</td>
        <td contenteditable="true">${esc(r["Quantity"] || '')}</td>
        <td contenteditable="true">${esc(r["Uom"] || '')}</td>
        <td contenteditable="true">${esc(r["Net Weight (KG)"] || '')}</td>
        <td contenteditable="true">${esc(r["SO No"] || '')}</td>
        <td contenteditable="true">${esc(r["Invoice No"] || '')}</td>
        <td contenteditable="true">${esc(r["Line No"] || '')}</td>
        <td contenteditable="true">${esc(r["Packing Size"] || '')}</td>
        <td>${esc(r["Full Cartons"] ?? '')}</td>
        <td>${esc(r["Loose Qty"] ?? '')}</td>
        <td>${esc(r["Total Cartons"] ?? '')}</td>
        <td class="${noteClass(r["Note"])}">${esc(r["Note"] || 'OK')}</td>
      </tr>`);
  });
}

function syncResultRowsFromTable(){
  const rows = Array.from(resultTableBody.querySelectorAll('tr'));
  state.reviewRows = rows.map(tr => {
    const tds = tr.querySelectorAll('td');
    return {
      "ASN No": tds[0].innerText.trim(), "PO No": tds[1].innerText.trim(), "Item No": tds[2].innerText.trim(),
      "Rev": tds[3].innerText.trim(), "Quantity": toNumberOrText(tds[4].innerText.trim()),
      "Uom": tds[5].innerText.trim(), "Net Weight (KG)": toNumberOrText(tds[6].innerText.trim()),
      "SO No": tds[7].innerText.trim(), "Invoice No": tds[8].innerText.trim(), "Line No": tds[9].innerText.trim(),
      "Packing Size": toNumberOrText(tds[10].innerText.trim()), "Full Cartons": toNumberOrText(tds[11].innerText.trim()),
      "Loose Qty": toNumberOrText(tds[12].innerText.trim()), "Total Cartons": toNumberOrText(tds[13].innerText.trim()),
      "Note": tds[14].innerText.trim(),
    };
  });
}

function calcSummaryRows(){
  let cptFull=0,cptLoose=0,cptTotal=0, opFull=0,opLoose=0,opTotal=0, gpFull=0,gpLoose=0,gpTotal=0;
  state.reviewRows.forEach(r => {
    const line = String(r["Line No"] || '').toUpperCase().trim();
    const full = Number(r["Full Cartons"] || 0) || 0;
    const looseQty = Number(r["Loose Qty"] || 0) || 0;
    const total = Number(r["Total Cartons"] || 0) || 0;
    const looseCartons = looseQty > 0 ? 1 : 0;
    if (line.startsWith('C2')) { cptFull += full; cptLoose += looseCartons; cptTotal += total; }
    else if (line.startsWith('C1')) { opFull += full; opLoose += looseCartons; opTotal += total; }
    else if (line.startsWith('GP') || line.includes('GP JOB')) { gpFull += full; gpLoose += looseCartons; gpTotal += total; }
  });
  return [{loc:'CPT', full:cptFull, loose:cptLoose, total:cptTotal},{loc:'OP', full:opFull, loose:opLoose, total:opTotal},{loc:'GP', full:gpFull, loose:gpLoose, total:gpTotal}];
}

function renderCartonSummary(){
  cartonSummary.innerHTML = calcSummaryRows().map(r => `<tr><td>${r.loc}</td><td>${r.full}</td><td>${r.loose}</td><td>${r.total}</td></tr>`).join('');
}

function renderSummary(summary){
  etaBadge.textContent = `ETA sớm nhất: ${state.earliestEta || '-'}`;
  summaryBadge.textContent = `ASN ${summary.total_asn || 0} • Missing ${summary.missing_packing || 0}`;
  renderCartonSummary();
}

function renderPackingTables(){
  packingBody.innerHTML = '';
  pairBody.innerHTML = '';
  const singleRows = state.singlePacking.length ? state.singlePacking : [{"Item":"", "Rev":"01", "Qty":""}];
  const pairRows = state.pairPacking.length ? state.pairPacking : [{"Item A":"", "Rev A":"01", "Item B":"", "Rev B":"01", "Qty":""}];
  singleRows.forEach(r => packingBody.insertAdjacentHTML('beforeend', `<tr><td contenteditable="true">${esc(r["Item"] || '')}</td><td contenteditable="true">${esc(r["Rev"] || '')}</td><td contenteditable="true">${esc(r["Qty"] || '')}</td></tr>`));
  pairRows.forEach(r => pairBody.insertAdjacentHTML('beforeend', `<tr><td contenteditable="true">${esc(r["Item A"] || '')}</td><td contenteditable="true">${esc(r["Rev A"] || '')}</td><td contenteditable="true">${esc(r["Item B"] || '')}</td><td contenteditable="true">${esc(r["Rev B"] || '')}</td><td contenteditable="true">${esc(r["Qty"] || '')}</td></tr>`));
}

function readSinglePacking(){
  return Array.from(packingBody.querySelectorAll('tr')).map(tr => {
    const tds = tr.querySelectorAll('td');
    return {"Item": tds[0]?.innerText.trim() || '', "Rev": tds[1]?.innerText.trim() || '', "Qty": toNumberOrText(tds[2]?.innerText.trim() || '')};
  }).filter(r => r.Item);
}
function readPairPacking(){
  return Array.from(pairBody.querySelectorAll('tr')).map(tr => {
    const tds = tr.querySelectorAll('td');
    return {"Item A": tds[0]?.innerText.trim() || '', "Rev A": tds[1]?.innerText.trim() || '', "Item B": tds[2]?.innerText.trim() || '', "Rev B": tds[3]?.innerText.trim() || '', "Qty": toNumberOrText(tds[4]?.innerText.trim() || '')};
  }).filter(r => r["Item A"] || r["Item B"]);
}

async function loadInitialState(){
  try{
    const res = await fetch('/api/state');
    const data = await res.json();
    state.headers = data.headers || [];
    state.rawLines = data.raw_lines || [];
    state.reviewRows = data.review_rows || [];
    state.earliestEta = data.earliest_eta || '';
    state.singlePacking = data.single_packing || [];
    state.pairPacking = data.pair_packing || [];
    renderHeaders(); renderResultTable(); renderSummary(data.summary || {}); renderPackingTables();
  }catch(err){ setStatus(`Lỗi tải trạng thái: ${err.message}`, 'error'); }
}

scanBtn?.addEventListener('click', async () => {
  if (!state.files.length) return setStatus('Bạn chưa chọn file PDF.', 'error');
  setStatus('Đang parse PDF...', 'muted');
  const form = new FormData();
  state.files.forEach(f => form.append('files', f, f.name));
  try{
    const res = await fetch('/api/parse', {method:'POST', body: form});
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Parse failed');
    state.headers = data.headers || []; state.rawLines = data.raw_lines || []; state.reviewRows = data.review_rows || []; state.earliestEta = data.earliest_eta || '';
    renderHeaders(); renderResultTable(); renderSummary(data.summary || {});
    setStatus(`Đã đọc ${state.headers.length} ASN.`, 'ok');
    document.querySelector('.tab[data-tab="result"]').click();
  }catch(err){ setStatus(`Lỗi parse: ${err.message}`, 'error'); }
});

qs('recalculateBtn')?.addEventListener('click', async () => {
  syncResultRowsFromTable();
  try{
    const res = await fetch('/api/recalculate', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({headers: state.headers, raw_lines: state.rawLines, review_rows: state.reviewRows})});
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Recalculate failed');
    state.reviewRows = data.review_rows || []; renderResultTable(); renderSummary(data.summary || {});
    setStatus('Đã tính lại dữ liệu.', 'ok');
  }catch(err){ setStatus(`Lỗi recalculate: ${err.message}`, 'error'); }
});

async function doExport(){
  syncResultRowsFromTable();
  if (!state.headers.length || !state.reviewRows.length) return setStatus('Chưa có dữ liệu để export.', 'error');
  try{
    const res = await fetch('/api/export', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({headers: state.headers, raw_lines: state.rawLines, review_rows: state.reviewRows})});
    if (!res.ok) throw new Error(await res.text());
    window.location.href = '/api/export';
    setStatus('Đang xuất Excel...', 'ok');
  }catch(err){ setStatus(`Lỗi export: ${err.message}`, 'error'); }
}
qs('exportBtnTop')?.addEventListener('click', doExport);
qs('exportBtnBottom')?.addEventListener('click', doExport);

qs('addRowBtn')?.addEventListener('click', () => { state.singlePacking.push({"Item":"", "Rev":"01", "Qty":""}); renderPackingTables(); });
qs('addPairRowBtn')?.addEventListener('click', () => { state.pairPacking.push({"Item A":"", "Rev A":"01", "Item B":"", "Rev B":"01", "Qty":""}); renderPackingTables(); });

qs('savePackingBtn')?.addEventListener('click', async () => {
  try{
    const res = await fetch('/api/packing/single/save', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({rows: readSinglePacking()})});
    const data = await res.json(); if (!res.ok) throw new Error(data.detail || 'Save single failed');
    state.singlePacking = data.rows || []; renderPackingTables(); setStatus('Đã lưu Packing Mã đơn.', 'ok');
  }catch(err){ setStatus(`Lỗi save packing: ${err.message}`, 'error'); }
});

qs('savePairBtn')?.addEventListener('click', async () => {
  try{
    const res = await fetch('/api/packing/pair/save', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({rows: readPairPacking()})});
    const data = await res.json(); if (!res.ok) throw new Error(data.detail || 'Save pair failed');
    state.pairPacking = data.rows || []; renderPackingTables(); setStatus('Đã lưu Packing Mã đôi.', 'ok');
  }catch(err){ setStatus(`Lỗi save pair: ${err.message}`, 'error'); }
});

qs('singleImportInput')?.addEventListener('change', async (e) => {
  const file = e.target.files?.[0]; if (!file) return;
  const form = new FormData(); form.append('file', file, file.name); form.append('mode', 'append');
  try{
    const res = await fetch('/api/packing/single/import', {method:'POST', body: form});
    const data = await res.json(); if (!res.ok) throw new Error(data.detail || 'Import single failed');
    state.singlePacking = data.rows || []; renderPackingTables(); setStatus('Đã import Packing Mã đơn.', 'ok');
  }catch(err){ setStatus(`Lỗi import single: ${err.message}`, 'error'); }
});

qs('pairImportInput')?.addEventListener('change', async (e) => {
  const file = e.target.files?.[0]; if (!file) return;
  const form = new FormData(); form.append('file', file, file.name); form.append('mode', 'append');
  try{
    const res = await fetch('/api/packing/pair/import', {method:'POST', body: form});
    const data = await res.json(); if (!res.ok) throw new Error(data.detail || 'Import pair failed');
    state.pairPacking = data.rows || []; renderPackingTables(); setStatus('Đã import Packing Mã đôi.', 'ok');
  }catch(err){ setStatus(`Lỗi import pair: ${err.message}`, 'error'); }
});

qs('packingSearch')?.addEventListener('input', e => {
  const keyword = e.target.value.toLowerCase().trim();
  Array.from(packingBody.querySelectorAll('tr')).forEach(row => row.style.display = row.innerText.toLowerCase().includes(keyword) ? '' : 'none');
});

loadInitialState();
