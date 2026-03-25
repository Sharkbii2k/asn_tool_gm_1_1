const state = {
  files: [],
  headers: [],
  rawLines: [],
  reviewRows: [],
  earliestEta: '',
  singlePacking: [],
  pairPacking: [],
};

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

tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.tab;
    tabs.forEach(t => t.classList.remove('active'));
    panels.forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(`tab-${target}`).classList.add('active');
  });
});

function setStatus(text, type='muted'){
  scanStatus.textContent = text;
  scanStatus.className = `status-box ${type}`;
}

fileInput?.addEventListener('change', () => {
  state.files = Array.from(fileInput.files || []);
  if (!state.files.length) {
    fileList.textContent = 'Chưa có file nào được chọn.';
    fileList.classList.add('empty');
    return;
  }
  fileList.classList.remove('empty');
  fileList.innerHTML = state.files.map((f, i) => `${i + 1}. ${f.name}`).join('<br>');
});

function esc(v){
  if (v === null || v === undefined) return '';
  return String(v)
    .replaceAll('&','&amp;')
    .replaceAll('<','&lt;')
    .replaceAll('>','&gt;')
    .replaceAll('"','&quot;');
}

function renderHeaders(){
  headerBody.innerHTML = '';
  if (!state.headers.length) {
    headerBody.innerHTML = `<tr><td colspan="5">Chưa có dữ liệu.</td></tr>`;
    headerCountBadge.textContent = '0 ASN';
    return;
  }
  state.headers.forEach(r => {
    headerBody.insertAdjacentHTML('beforeend', `
      <tr>
        <td>${esc(r["ASN No"])}</td>
        <td>${esc(r["ETA"])}</td>
        <td>${esc(r["ETD"] || '-')}</td>
        <td>${esc(r["Sold To"])}</td>
        <td>${esc(r["Bill To"])}</td>
      </tr>
    `);
  });
  headerCountBadge.textContent = `${state.headers.length} ASN`;
}

function rowNoteClass(note){
  return String(note || '').trim() === 'No Packing' ? 'warn-note' : 'ok-note';
}

function resultCell(value, cls=''){
  return `<td class="${cls}" contenteditable="true">${esc(value ?? '')}</td>`;
}

function renderResultTable(){
  resultTableBody.innerHTML = '';
  if (!state.reviewRows.length) {
    resultTableBody.innerHTML = `<tr><td colspan="15">Chưa có dữ liệu.</td></tr>`;
    return;
  }
  state.reviewRows.forEach((r, idx) => {
    resultTableBody.insertAdjacentHTML('beforeend', `
      <tr data-idx="${idx}">
        ${resultCell(r["ASN No"])}
        ${resultCell(r["PO No"])}
        ${resultCell(r["Item No"])}
        ${resultCell(r["Rev"])}
        ${resultCell(r["Quantity"])}
        ${resultCell(r["Uom"])}
        ${resultCell(r["Net Weight (KG)"])}
        ${resultCell(r["SO No"])}
        ${resultCell(r["Invoice No"])}
        ${resultCell(r["Line No"])}
        ${resultCell(r["Packing Size"])}
        <td>${esc(r["Full Cartons"] ?? '')}</td>
        <td>${esc(r["Loose Qty"] ?? '')}</td>
        <td>${esc(r["Total Cartons"] ?? '')}</td>
        <td class="${rowNoteClass(r["Note"])}">${esc(r["Note"] || 'OK')}</td>
      </tr>
    `);
  });
}

function syncResultRowsFromTable(){
  const rows = Array.from(resultTableBody.querySelectorAll('tr'));
  state.reviewRows = rows.map(tr => {
    const tds = tr.querySelectorAll('td');
    return {
      "ASN No": tds[0].innerText.trim(),
      "PO No": tds[1].innerText.trim(),
      "Item No": tds[2].innerText.trim(),
      "Rev": tds[3].innerText.trim(),
      "Quantity": toNumberOrText(tds[4].innerText.trim()),
      "Uom": tds[5].innerText.trim(),
      "Net Weight (KG)": toNumberOrText(tds[6].innerText.trim()),
      "SO No": tds[7].innerText.trim(),
      "Invoice No": tds[8].innerText.trim(),
      "Line No": tds[9].innerText.trim(),
      "Packing Size": toNumberOrText(tds[10].innerText.trim()),
      "Full Cartons": toNumberOrText(tds[11].innerText.trim()),
      "Loose Qty": toNumberOrText(tds[12].innerText.trim()),
      "Total Cartons": toNumberOrText(tds[13].innerText.trim()),
      "Note": tds[14].innerText.trim(),
    };
  });
}

function toNumberOrText(v){
  if (v === '') return '';
  const num = Number(v);
  return Number.isNaN(num) ? v : num;
}

function calcSummaryRows(){
  let cptFull=0,cptLoose=0,cptTotal=0;
  let opFull=0,opLoose=0,opTotal=0;
  let gpFull=0,gpLoose=0,gpTotal=0;

  state.reviewRows.forEach(r => {
    const line = String(r["Line No"] || '').toUpperCase().trim();
    const full = Number(r["Full Cartons"] || 0) || 0;
    const looseQty = Number(r["Loose Qty"] || 0) || 0;
    const total = Number(r["Total Cartons"] || 0) || 0;
    const looseCartons = looseQty > 0 ? 1 : 0;
    if (line.startsWith('C2')) {
      cptFull += full; cptLoose += looseCartons; cptTotal += total;
    } else if (line.startsWith('C1')) {
      opFull += full; opLoose += looseCartons; opTotal += total;
    } else if (line.startsWith('GP') || line.includes('GP JOB')) {
      gpFull += full; gpLoose += looseCartons; gpTotal += total;
    }
  });

  return [
    {loc:'CPT', full:cptFull, loose:cptLoose, total:cptTotal},
    {loc:'OP', full:opFull, loose:opLoose, total:opTotal},
    {loc:'GP', full:gpFull, loose:gpLoose, total:gpTotal},
  ];
}

function renderCartonSummary(){
  const rows = calcSummaryRows();
  cartonSummary.innerHTML = rows.map(r => `
    <tr>
      <td>${r.loc}</td>
      <td>${r.full}</td>
      <td>${r.loose}</td>
      <td>${r.total}</td>
    </tr>
  `).join('');
}

function renderSummary(summary){
  etaBadge.textContent = `ETA sớm nhất: ${state.earliestEta || '-'}`;
  summaryBadge.textContent = `ASN ${summary.total_asn || 0} • Missing Packing ${summary.missing_packing || 0}`;
  renderCartonSummary();
}

function packingRowHtml(r){
  return `
    <tr>
      <td contenteditable="true">${esc(r["Item"] || '')}</td>
      <td contenteditable="true">${esc(r["Rev"] || '')}</td>
      <td contenteditable="true">${esc(r["Qty"] || '')}</td>
    </tr>
  `;
}
function pairRowHtml(r){
  return `
    <tr>
      <td contenteditable="true">${esc(r["Item A"] || '')}</td>
      <td contenteditable="true">${esc(r["Rev A"] || '')}</td>
      <td contenteditable="true">${esc(r["Item B"] || '')}</td>
      <td contenteditable="true">${esc(r["Rev B"] || '')}</td>
      <td contenteditable="true">${esc(r["Qty"] || '')}</td>
    </tr>
  `;
}
function renderPackingTables(){
  packingBody.innerHTML = state.singlePacking.length ? state.singlePacking.map(packingRowHtml).join('') : `<tr><td colspan="3">Chưa có packing.</td></tr>`;
  pairBody.innerHTML = state.pairPacking.length ? state.pairPacking.map(pairRowHtml).join('') : `<tr><td colspan="5">Chưa có pair packing.</td></tr>`;
}
function readPackingTable(){
  const rows = Array.from(packingBody.querySelectorAll('tr'));
  return rows.map(tr => {
    const td = tr.querySelectorAll('td');
    return {"Item": td[0]?.innerText.trim() || '', "Rev": td[1]?.innerText.trim() || '', "Qty": toNumberOrText(td[2]?.innerText.trim() || '')};
  }).filter(r => r.Item);
}
function readPairTable(){
  const rows = Array.from(pairBody.querySelectorAll('tr'));
  return rows.map(tr => {
    const td = tr.querySelectorAll('td');
    return {
      "Item A": td[0]?.innerText.trim() || '',
      "Rev A": td[1]?.innerText.trim() || '',
      "Item B": td[2]?.innerText.trim() || '',
      "Rev B": td[3]?.innerText.trim() || '',
      "Qty": toNumberOrText(td[4]?.innerText.trim() || '')
    };
  }).filter(r => r["Item A"] || r["Item B"]);
}

async function loadPacking(){
  const [singleRes, pairRes] = await Promise.all([
    fetch('/api/packing/single'),
    fetch('/api/packing/pair')
  ]);
  const singleData = await singleRes.json();
  const pairData = await pairRes.json();
  state.singlePacking = singleData.rows || [];
  state.pairPacking = pairData.rows || [];
  renderPackingTables();
}

scanBtn?.addEventListener('click', async () => {
  if (!state.files.length) {
    setStatus('Bạn chưa chọn file.', 'error');
    return;
  }
  setStatus('Đang parse PDF...', 'muted');
  const form = new FormData();
  state.files.forEach(f => form.append('files', f, f.name));
  try {
    const res = await fetch('/api/parse', {method:'POST', body: form});
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    state.headers = data.headers || [];
    state.rawLines = data.raw_lines || [];
    state.reviewRows = data.review_rows || [];
    state.earliestEta = data.earliest_eta || '';
    renderHeaders();
    renderResultTable();
    renderSummary(data.summary || {});
    setStatus(`Đã đọc ${state.headers.length} ASN.`, 'ok');
    tabs.forEach(t => t.classList.remove('active'));
    panels.forEach(p => p.classList.remove('active'));
    document.querySelector('.tab[data-tab="result"]').classList.add('active');
    document.getElementById('tab-result').classList.add('active');
  } catch (e) {
    setStatus(`Lỗi parse: ${e.message}`, 'error');
  }
});

qs('recalculateBtn')?.addEventListener('click', async () => {
  syncResultRowsFromTable();
  try {
    const res = await fetch('/api/recalculate', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({headers: state.headers, review_rows: state.reviewRows})
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    state.reviewRows = data.review_rows || [];
    renderResultTable();
    renderSummary(data.summary || {});
    setStatus('Đã tính lại dữ liệu.', 'ok');
  } catch (e) {
    setStatus(`Lỗi recalculate: ${e.message}`, 'error');
  }
});

async function doExport(){
  syncResultRowsFromTable();
  if (!state.headers.length || !state.reviewRows.length) {
    setStatus('Chưa có dữ liệu để export.', 'error');
    return;
  }
  try {
    const res = await fetch('/api/export', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        headers: state.headers,
        raw_lines: state.rawLines,
        review_rows: state.reviewRows
      })
    });
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const cd = res.headers.get('Content-Disposition') || '';
    let filename = 'ASN_export.xlsx';
    const match = cd.match(/filename="([^"]+)"/);
    if (match) filename = match[1];
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    setStatus(`Đã export ${filename}`, 'ok');
  } catch (e) {
    setStatus(`Lỗi export: ${e.message}`, 'error');
  }
}
qs('exportBtnTop')?.addEventListener('click', doExport);
qs('exportBtnBottom')?.addEventListener('click', doExport);

qs('addRowBtn')?.addEventListener('click', () => {
  state.singlePacking.push({"Item":"", "Rev":"01", "Qty":""});
  renderPackingTables();
});
qs('addPairRowBtn')?.addEventListener('click', () => {
  state.pairPacking.push({"Item A":"", "Rev A":"01", "Item B":"", "Rev B":"01", "Qty":""});
  renderPackingTables();
});

qs('savePackingBtn')?.addEventListener('click', async () => {
  try {
    const rows = readPackingTable();
    const res = await fetch('/api/packing/single/save', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({rows})
    });
    const data = await res.json();
    state.singlePacking = data.rows || [];
    renderPackingTables();
    setStatus('Đã lưu Single Packing.', 'ok');
  } catch (e) {
    setStatus(`Lỗi save packing: ${e.message}`, 'error');
  }
});

qs('savePairBtn')?.addEventListener('click', async () => {
  try {
    const rows = readPairTable();
    const res = await fetch('/api/packing/pair/save', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({rows})
    });
    const data = await res.json();
    state.pairPacking = data.rows || [];
    renderPackingTables();
    setStatus('Đã lưu Pair Packing.', 'ok');
  } catch (e) {
    setStatus(`Lỗi save pair: ${e.message}`, 'error');
  }
});

qs('singleImportInput')?.addEventListener('change', async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  const form = new FormData();
  form.append('file', file, file.name);
  form.append('mode', 'append');
  try {
    const res = await fetch('/api/packing/single/import', {method:'POST', body: form});
    const data = await res.json();
    state.singlePacking = data.rows || [];
    renderPackingTables();
    setStatus('Đã import Single Packing.', 'ok');
  } catch (err) {
    setStatus(`Lỗi import packing: ${err.message}`, 'error');
  }
});

qs('pairImportInput')?.addEventListener('change', async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  const form = new FormData();
  form.append('file', file, file.name);
  form.append('mode', 'append');
  try {
    const res = await fetch('/api/packing/pair/import', {method:'POST', body: form});
    const data = await res.json();
    state.pairPacking = data.rows || [];
    renderPackingTables();
    setStatus('Đã import Pair Packing.', 'ok');
  } catch (err) {
    setStatus(`Lỗi import pair: ${err.message}`, 'error');
  }
});

qs('packingSearch')?.addEventListener('input', e => {
  const keyword = e.target.value.toLowerCase().trim();
  const rows = Array.from(packingBody.querySelectorAll('tr'));
  rows.forEach(row => {
    const txt = row.innerText.toLowerCase();
    row.style.display = txt.includes(keyword) ? '' : 'none';
  });
});

loadPacking();
renderHeaders();
renderResultTable();
renderCartonSummary();