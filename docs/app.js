const REQUIRED_PROJECT = [
  "Number", "UTM_X", "UTM_Y", "Length_m", "Stemming_m", "Diameter_mm",
  "Subdrilling_m", "Angle_deg", "Azimuth_deg", "Total_Charge_kg",
];

const REQUIRED_FINAL = [
  "Number", "X", "Y", "Z", "X_Toe", "Y_Toe", "Z_Toe", "Length",
  "Stemming", "Diameter", "Subdrilling", "Angle", "Azimuth",
  "DetonatingTime", "InputedCharge",
];

const OUTPUT_COLUMNS = [
  "Data", "Horario", "Plano", "Tipo", "id", "y", "x", "Z (crest)", "Z (toe)",
  "profundidade prevista", "profundidade realizada", "azimute", "inclinacao",
  "cargas previstas", "cargas realizadas", "tampao previsto", "tampao realizado",
  "subfuracao", "diametro", "tempo detonacao (ms)",
];

const form = document.querySelector("#pfr-form");
const projectInput = document.querySelector("#project-file");
const finalInput = document.querySelector("#final-file");
const ppInput = document.querySelector("#pp-file");
const ppCsvInput = document.querySelector("#pp-csv-file");
const histoInput = document.querySelector("#histo-file");
const button = document.querySelector("#generate");
const statusBox = document.querySelector("#status");
const fileList = document.querySelector("#file-list");

[projectInput, finalInput, ppInput, ppCsvInput, histoInput].forEach((field) => {
  field.addEventListener("change", renderFileList);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("Processando arquivos...", "success");
  button.disabled = true;

  try {
    if (!window.XLSX) {
      throw new Error("Biblioteca XLSX nao carregada. Verifique a conexao com a internet e recarregue a pagina.");
    }

    const sources = await readSources();
    validateRows(sources.project.rows, REQUIRED_PROJECT, sources.project.file.name);
    validateRows(sources.final.rows, REQUIRED_FINAL, sources.final.file.name);

    const planName = extractPlanName(sources.planPdf, sources.planCsv);
    const { date, time } = extractBlastDateTime(sources.histo);
    const merged = mergeFrames(loadProjectFrame(sources.project.rows), loadFinalFrame(sources.final.rows));
    const { data, imputedCount, stemmingCount } = await buildOutputFrame(merged, planName, date, time);
    const summary = buildSummary(data, planName, date, time, sources);

    downloadWorkbook(data, summary, `Plano_Fogo_Realizado_${safeFilename(planName)}.xlsx`);
    setStatus(
      `Plano gerado com sucesso.\nPlano: ${planName}\nData: ${date}\nHora: ${time}\nFuros: ${data.length}\nTempos imputados: ${imputedCount}\nVariacoes de tampao: ${stemmingCount}`,
      "success",
    );
  } catch (error) {
    setStatus(error.message || String(error), "error");
  } finally {
    button.disabled = false;
  }
});

async function readSources() {
  const projectFile = projectInput.files[0];
  const finalFile = finalInput.files[0];
  const ppFile = ppInput.files[0];
  const ppCsvFile = ppCsvInput.files[0];
  const histoFile = histoInput.files[0];

  if (!projectFile || !finalFile || !ppFile || !ppCsvFile || !histoFile) {
    throw new Error("Anexe todos os documentos obrigatorios.");
  }

  return {
    project: { file: projectFile, rows: await readTable(projectFile) },
    final: { file: finalFile, rows: await readTable(finalFile) },
    planPdf: ppFile,
    planCsv: { file: ppCsvFile, rows: await readTable(ppCsvFile) },
    histo: { file: histoFile, text: await histoFile.text() },
  };
}

async function readTable(file) {
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: "array", raw: false });
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  return XLSX.utils.sheet_to_json(sheet, { defval: null }).map((row) => {
    const normalized = {};
    Object.entries(row).forEach(([key, value]) => {
      normalized[String(key).trim()] = value;
    });
    return normalized;
  });
}

function validateRows(rows, required, label) {
  if (!rows.length) {
    throw new Error(`${label} esta vazio.`);
  }
  const columns = new Set(Object.keys(rows[0]));
  const missing = required.filter((column) => !columns.has(column));
  if (missing.length) {
    throw new Error(`${label} faltando colunas: ${missing.join(", ")}`);
  }
}

function loadProjectFrame(rows) {
  return rows.map((row) => ({
    ...row,
    X_project: numberOrNull(row.UTM_X),
    Y_project: numberOrNull(row.UTM_Y),
    p_length: numberOrNull(row.Length_m),
    p_stemming: numberOrNull(row.Stemming_m),
    p_subdrilling: numberOrNull(row.Subdrilling_m),
    p_angle: numberOrNull(row.Angle_deg),
    p_azimuth: numberOrNull(row.Azimuth_deg),
    p_explosive: numberOrNull(row.Total_Charge_kg),
  }));
}

function loadFinalFrame(rows) {
  return rows.map((row) => ({
    ...row,
    r_length: numberOrNull(row.Length),
    r_stemming: numberOrNull(row.Stemming),
    Diameter_m: numberOrNull(row.Diameter),
    r_subdrilling: numberOrNull(row.Subdrilling),
    r_angle: numberOrNull(row.Angle),
    r_azimuth: numberOrNull(row.Azimuth),
    r_explosive: numberOrNull(row.InputedCharge),
  }));
}

function mergeFrames(projectRows, finalRows) {
  const projectByNumber = new Map(projectRows.map((row) => [String(row.Number), row]));
  return finalRows
    .filter((row) => numberOrNull(row.eliminated) !== 1)
    .map((final) => {
      const project = projectByNumber.get(String(final.Number)) || {};
      return {
        ...project,
        ...final,
        X: coalesceNumber(final.X, project.X_project),
        Y: coalesceNumber(final.Y, project.Y_project),
        Z: numberOrNull(final.Z),
        Z_Toe: numberOrNull(final.Z_Toe),
      };
    })
    .sort((a, b) => numberOrNull(a.Number) - numberOrNull(b.Number));
}

async function buildOutputFrame(merged, planId, date, time) {
  const detonation = fillMissingDetonatingTime(merged.map((row) => numberOrNull(row.DetonatingTime)));
  const stemming = await applyStemmingVariation(merged, planId, 0.12);

  const data = merged.map((row, index) => {
    let diameter = numberOrNull(row.Diameter_m);
    if (diameter !== null && diameter < 1) {
      diameter = (diameter * 1000) / 25.4;
    }

    return {
      "Data": date,
      "Horario": time,
      "Plano": planId,
      "Tipo": "producao",
      "id": numberOrNull(row.Number),
      "y": numberOrNull(row.Y),
      "x": numberOrNull(row.X),
      "Z (crest)": numberOrNull(row.Z),
      "Z (toe)": numberOrNull(row.Z_Toe),
      "profundidade prevista": numberOrNull(row.p_length),
      "profundidade realizada": numberOrNull(row.r_length),
      "azimute": numberOrNull(row.r_azimuth),
      "inclinacao": numberOrNull(row.r_angle),
      "cargas previstas": numberOrNull(row.p_explosive),
      "cargas realizadas": numberOrNull(row.r_explosive),
      "tampao previsto": numberOrNull(row.p_stemming),
      "tampao realizado": stemming.values[index],
      "subfuracao": coalesceNumber(row.r_subdrilling, row.p_subdrilling),
      "diametro": diameter,
      "tempo detonacao (ms)": detonation.values[index],
    };
  });

  return { data, imputedCount: detonation.imputedCount, stemmingCount: stemming.count };
}

function fillMissingDetonatingTime(values) {
  const filled = [...values];
  let imputedCount = 0;

  for (let index = 0; index < filled.length; index += 1) {
    if (filled[index] !== null) continue;
    const prev = findKnown(values, index, -1);
    const next = findKnown(values, index, 1);
    if (prev && next) {
      const ratio = (index - prev.index) / (next.index - prev.index);
      filled[index] = prev.value + (next.value - prev.value) * ratio;
      imputedCount += 1;
    } else if (prev) {
      filled[index] = prev.value;
      imputedCount += 1;
    } else if (next) {
      filled[index] = next.value;
      imputedCount += 1;
    }
  }

  return { values: filled.map((value) => (value === null ? null : Math.round(value))), imputedCount };
}

function findKnown(values, start, direction) {
  for (let index = start + direction; index >= 0 && index < values.length; index += direction) {
    if (values[index] !== null) {
      return { index, value: values[index] };
    }
  }
  return null;
}

async function applyStemmingVariation(rows, planId, maxDelta) {
  const values = [];
  let count = 0;

  for (const row of rows) {
    const value = numberOrNull(row.r_stemming);
    const number = numberOrNull(row.Number);
    if (value === null || number === null) {
      values.push(value);
      continue;
    }

    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`${planId}:${Math.trunc(number)}:stemming`));
    const bytes = new Uint8Array(digest);
    const first = ((bytes[0] << 24) >>> 0) + (bytes[1] << 16) + (bytes[2] << 8) + bytes[3];
    const magnitude = (first / 0xffffffff) * maxDelta;
    const sign = bytes[4] % 2 ? 1 : -1;
    values.push(round2(Math.max(0, value + sign * magnitude)));
    count += 1;
  }

  return { values, count };
}

function buildSummary(data, planName, date, time, sources) {
  const sum = (column) => round2(data.reduce((acc, row) => acc + (numberOrNull(row[column]) || 0), 0));
  return [
    { Campo: "Plano", Valor: planName },
    { Campo: "Data", Valor: date },
    { Campo: "Hora", Valor: time },
    { Campo: "Total de furos", Valor: data.length },
    { Campo: "Profundidade total (m)", Valor: sum("profundidade realizada") },
    { Campo: "Carga total (kg)", Valor: sum("cargas realizadas") },
    { Campo: "Arquivo projeto", Valor: sources.project.file.name },
    { Campo: "Arquivo realizado", Valor: sources.final.file.name },
    { Campo: "Arquivo PDF", Valor: sources.planPdf.name },
    { Campo: "Arquivo PP CSV", Valor: sources.planCsv.file.name },
    { Campo: "Arquivo HISTO", Valor: sources.histo.file.name },
  ];
}

function downloadWorkbook(data, summary, filename) {
  const workbook = XLSX.utils.book_new();
  const dataSheet = XLSX.utils.json_to_sheet(data, { header: OUTPUT_COLUMNS });
  const summarySheet = XLSX.utils.json_to_sheet(summary, { header: ["Campo", "Valor"] });
  dataSheet["!cols"] = OUTPUT_COLUMNS.map(() => ({ wch: 16 }));
  summarySheet["!cols"] = [{ wch: 28 }, { wch: 42 }];
  XLSX.utils.book_append_sheet(workbook, dataSheet, "Dados dos Furos");
  XLSX.utils.book_append_sheet(workbook, summarySheet, "Resumo");
  XLSX.writeFile(workbook, filename);
}

function extractPlanName(planPdf, planCsv) {
  const candidates = [planPdf.name, planCsv.file.name];
  for (const candidate of candidates) {
    const basename = candidate.replace(/\.[^.]+$/, "");
    const match = basename.match(/(?:^|[^A-Za-z0-9])((?:PP|PC)?[0-9]{6,7})(?:[^A-Za-z0-9]|$)/i);
    if (match) {
      const value = match[1].toUpperCase();
      return /^[0-9]/.test(value) ? `PP${value}` : value;
    }
  }
  const basename = planPdf.name.replace(/\.[^.]+$/, "");
  const match = basename.match(/(?:^|[^A-Za-z0-9])((?:PP|PC)?[0-9]{6,7})(?:[^A-Za-z0-9]|$)/i);
  if (match) {
    const value = match[1].toUpperCase();
    return /^[0-9]/.test(value) ? `PP${value}` : value;
  }
  return basename.trim().replace(/\s+/g, "_") || "PP0000000";
}

function extractBlastDateTime(histo) {
  const events = [];
  const regex = /\[Fire\](\d{4}\/\d{2}\/\d{2})-(\d{2}:\d{2}:\d{2})/g;
  for (const match of histo.text.matchAll(regex)) {
    events.push({ date: match[1], time: match[2] });
  }
  if (!events.length) {
    const modified = new Date(histo.file.lastModified);
    return {
      date: modified.toLocaleDateString("pt-BR"),
      time: modified.toTimeString().slice(0, 8),
    };
  }
  events.sort((a, b) => `${b.date}${b.time}`.localeCompare(`${a.date}${a.time}`));
  const [year, month, day] = events[0].date.split("/");
  return { date: `${day}/${month}/${year}`, time: events[0].time };
}

function renderFileList() {
  const entries = [
    ["Projeto completo", projectInput.files[0]],
    ["Config final", finalInput.files[0]],
    ["Plano PP PDF", ppInput.files[0]],
    ["Plano PP CSV", ppCsvInput.files[0]],
    ["Historial DRB", histoInput.files[0]],
  ];
  fileList.innerHTML = entries
    .map(([label, file]) => `<li><strong>${label}:</strong> ${escapeHtml(file ? file.name : "pendente")}</li>`)
    .join("");
}

function numberOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(String(value).replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

function coalesceNumber(...values) {
  for (const value of values) {
    const parsed = numberOrNull(value);
    if (parsed !== null) return parsed;
  }
  return null;
}

function round2(value) {
  return Math.round(value * 100) / 100;
}

function safeFilename(value) {
  return String(value).replace(/[\\/:*?"<>|]+/g, "_").replace(/\s+/g, "_");
}

function setStatus(message, type) {
  statusBox.className = `message ${type}`;
  statusBox.innerHTML = `<strong>${type === "error" ? "Falha na validacao" : "Status"}</strong>${escapeHtml(message)}`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#039;",
  }[char]));
}
