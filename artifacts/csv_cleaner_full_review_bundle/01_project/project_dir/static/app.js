const state = {
  csvText: '',
  cleanedCsv: '',
  columns: [],
};

const fileInput = document.getElementById('csvFile');
const fileName = document.getElementById('fileName');
const removeEmpty = document.getElementById('removeEmpty');
const removeDuplicates = document.getElementById('removeDuplicates');
const processBtn = document.getElementById('processBtn');
const exportBtn = document.getElementById('exportBtn');
const columnOptions = document.getElementById('columnOptions');
const rawTable = document.getElementById('rawTable');
const cleanedTable = document.getElementById('cleanedTable');
const inputRows = document.getElementById('inputRows');
const outputRows = document.getElementById('outputRows');
const removedRows = document.getElementById('removedRows');

fileInput.addEventListener('change', async () => {
  const file = fileInput.files[0];
  if (!file) return;
  fileName.textContent = file.name;
  state.csvText = await file.text();
  const lines = state.csvText.trim().split(/\r?\n/).slice(0, 1);
  if (lines.length) renderColumnOptions(lines[0].split(','));
});

processBtn.addEventListener('click', async () => {
  if (!state.csvText) {
    alert('Select a CSV file first.');
    return;
  }
  const keepColumns = Array.from(document.querySelectorAll('input[name="keepColumn"]:checked')).map((node) => node.value);
  const res = await fetch('/api/process', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      csv_text: state.csvText,
      remove_empty_rows: removeEmpty.checked,
      remove_duplicates: removeDuplicates.checked,
      keep_columns: keepColumns,
    }),
  });
  const doc = await res.json();
  state.cleanedCsv = doc.cleaned_csv;
  state.columns = doc.columns;
  renderTable(rawTable, doc.raw_preview);
  renderTable(cleanedTable, doc.cleaned_preview);
  inputRows.textContent = doc.stats.input_rows;
  outputRows.textContent = doc.stats.output_rows;
  removedRows.textContent = doc.stats.removed_empty_rows + doc.stats.removed_duplicate_rows;
  exportBtn.disabled = false;
});

exportBtn.addEventListener('click', () => {
  const blob = new Blob([state.cleanedCsv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'cleaned-data.csv';
  link.click();
  URL.revokeObjectURL(url);
});

function renderColumnOptions(columns) {
  columnOptions.innerHTML = '';
  columns.forEach((column) => {
    const label = document.createElement('label');
    label.className = 'column-chip';
    const box = document.createElement('input');
    box.type = 'checkbox';
    box.name = 'keepColumn';
    box.value = column.trim();
    box.checked = true;
    label.appendChild(box);
    label.append(` ${column.trim()}`);
    columnOptions.appendChild(label);
  });
}

function renderTable(target, rows) {
  if (!rows || !rows.length) {
    target.innerHTML = '<tr><td>No rows to show.</td></tr>';
    return;
  }
  const columns = Object.keys(rows[0]);
  const head = `<thead><tr>${columns.map((column) => `<th>${column}</th>`).join('')}</tr></thead>`;
  const body = `<tbody>${rows.map((row) => `<tr>${columns.map((column) => `<td>${row[column] ?? ''}</td>`).join('')}</tr>`).join('')}</tbody>`;
  target.innerHTML = head + body;
}
