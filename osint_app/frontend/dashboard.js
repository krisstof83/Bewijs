const LARGE_FILE_BYTES = 500 * 1024 * 1024;
const STORAGE_KEY = "disk_catalog_metadata_v2";
const PERSONS = ["Kristof Huibers", "Anneke Coenen", "Yolanda Dello"];

const state = {
  files: loadCatalog(),
  activeView: "all",
  sort: "name",
  reportHtml: "",
};

const el = {
  picker: document.getElementById("folderPicker"),
  totalFiles: document.getElementById("totalFiles"),
  totalDuplicates: document.getElementById("totalDuplicates"),
  totalLarge: document.getElementById("totalLarge"),
  totalSize: document.getElementById("totalSize"),
  viewTitle: document.getElementById("viewTitle"),
  all: document.getElementById("viewAll"),
  large: document.getElementById("viewLarge"),
  duplicates: document.getElementById("viewDuplicates"),
  folders: document.getElementById("viewFolders"),
  report: document.getElementById("viewReport"),
  overlay: document.getElementById("scanOverlay"),
  progressBar: document.getElementById("progressBar"),
  scanText: document.getElementById("scanText"),
  scanPercent: document.getElementById("scanPercent"),
  scanCounts: document.getElementById("scanCounts"),
  flyList: document.getElementById("flyList"),
};

setupEvents();
renderAll();

function setupEvents() {
  el.picker.addEventListener("change", async (event) => {
    const files = Array.from(event.target.files || []);
    if (files.length === 0) return;
    await runScan(files);
    el.picker.value = "";
  });

  document.querySelectorAll(".menu button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".menu button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeView = btn.dataset.view;
      renderViews();
    });
  });

  document.getElementById("sortByName").addEventListener("click", () => {
    state.sort = "name";
    renderViews();
  });

  document.getElementById("sortBySize").addEventListener("click", () => {
    state.sort = "size";
    renderViews();
  });

  document.getElementById("runAnalysis").addEventListener("click", () => {
    state.reportHtml = buildForensicReport(state.files);
    state.activeView = "report";
    document.querySelectorAll(".menu button").forEach((b) => b.classList.remove("active"));
    const reportBtn = document.querySelector('.menu button[data-view="report"]');
    if (reportBtn) reportBtn.classList.add("active");
    renderViews();
  });

  document.getElementById("clearCatalog").addEventListener("click", () => {
    state.files = [];
    state.reportHtml = "";
    persistCatalog();
    renderAll();
  });
}

async function runScan(inputFiles) {
  const scanned = [];

  el.overlay.classList.remove("hidden");
  el.flyList.innerHTML = "";
  for (let i = 0; i < inputFiles.length; i += 1) {
    const file = inputFiles[i];
    const relativePath = file.webkitRelativePath || file.name;
    const segments = relativePath.split("/");
    const source = segments[0] || "Lokale bron";

    const row = {
      id: `${Date.now()}-${i}-${Math.random().toString(16).slice(2)}`,
      name: file.name,
      size: file.size,
      source,
      fullPath: relativePath,
      folderPath: segments.slice(0, -1).join("/") || source,
      scannedAt: new Date().toISOString(),
      duplicateKey: `${file.name}|${file.size}`,
      isLarge: file.size >= LARGE_FILE_BYTES,
      lastModified: new Date(file.lastModified || Date.now()).toISOString(),
      type: file.type || extensionOf(file.name),
      excerpt: await safeExcerpt(file),
    };

    scanned.push(row);

    const progress = Math.round(((i + 1) / inputFiles.length) * 100);
    const tempList = state.files.concat(scanned);
    const tempDuplicateCount = countDuplicateItems(tempList);
    const tempLarge = tempList.filter((f) => f.isLarge).length;

    el.progressBar.style.width = `${progress}%`;
    el.scanPercent.textContent = `${progress}%`;
    el.scanText.textContent = `Verwerken: ${row.name}`;
    el.scanCounts.textContent = `${tempList.length} bestanden • ${tempDuplicateCount} duplicaten • ${tempLarge} rood`;

    const fly = document.createElement("div");
    fly.className = "fly-item";
    fly.textContent = `${row.name}  •  ${row.folderPath}`;
    el.flyList.prepend(fly);
    while (el.flyList.children.length > 30) {
      el.flyList.removeChild(el.flyList.lastChild);
    }

    await pause(8);
  }

  state.files = dedupeByFingerprint(state.files.concat(scanned));
  persistCatalog();
  state.reportHtml = "";
  renderAll();
  setTimeout(() => {
    el.overlay.classList.add("hidden");
  }, 220);
}

function renderAll() {
  renderStats();
  renderViews();
}

function renderStats() {
  const duplicateCount = countDuplicateItems(state.files);
  const largeCount = state.files.filter((f) => f.isLarge).length;
  const totalSize = state.files.reduce((sum, file) => sum + file.size, 0);

  el.totalFiles.textContent = String(state.files.length);
  el.totalDuplicates.textContent = String(duplicateCount);
  el.totalLarge.textContent = String(largeCount);
  el.totalSize.textContent = formatBytes(totalSize);
}

function renderViews() {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));

  const sorted = [...state.files].sort((a, b) => {
    if (state.sort === "size") return b.size - a.size;
    return a.name.localeCompare(b.name, "nl");
  });

  if (state.activeView === "all") {
    el.viewTitle.textContent = "Alle bestanden";
    el.all.classList.add("active");
    el.all.innerHTML = makeTable(sorted);
  }

  if (state.activeView === "large") {
    el.viewTitle.textContent = "Rode bestanden";
    el.large.classList.add("active");
    const largeFiles = sorted.filter((f) => f.isLarge).slice(0, 50);
    el.large.innerHTML = makeTable(largeFiles, true);
  }

  if (state.activeView === "duplicates") {
    el.viewTitle.textContent = "Dubbele bestanden";
    el.duplicates.classList.add("active");
    el.duplicates.innerHTML = renderDuplicateGroups(sorted);
  }

  if (state.activeView === "folders") {
    el.viewTitle.textContent = "Mappen en bron";
    el.folders.classList.add("active");
    el.folders.innerHTML = renderFolders(sorted);
  }

  if (state.activeView === "report") {
    el.viewTitle.textContent = "Forensisch rapport";
    el.report.classList.add("active");
    el.report.innerHTML = state.reportHtml || '<p>Klik op <strong>ANALYSE STARTEN</strong> om een dossier te genereren.</p>';
  }

  bindDeleteButtons();
}

function makeTable(rows, redMode = false) {
  if (rows.length === 0) return "<p>Geen bestanden gevonden in deze weergave.</p>";
  return `<table class="table"><thead><tr><th>Bestand</th><th>Grootte</th><th>Bron</th><th>Volledige bron (pad)</th><th>Actie</th></tr></thead><tbody>${rows
    .map(
      (file) => `<tr><td>${escapeHtml(file.name)}</td><td class="${redMode || file.isLarge ? "tag-red" : ""}">${formatBytes(file.size)}</td><td>${escapeHtml(file.source)}</td><td class="path">${escapeHtml(file.fullPath)}</td><td><button class="delete-item" data-id="${file.id}">Opruimen</button></td></tr>`,
    )
    .join("")}</tbody></table>`;
}

function renderDuplicateGroups(rows) {
  const groups = new Map();
  rows.forEach((file) => {
    const key = `${file.name}|${file.size}`;
    const list = groups.get(key) || [];
    list.push(file);
    groups.set(key, list);
  });

  const duplicateGroups = Array.from(groups.values())
    .filter((group) => group.length > 1)
    .sort((a, b) => b[0].size - a[0].size);

  if (duplicateGroups.length === 0) return "<p>Geen duplicaten gevonden.</p>";

  return duplicateGroups
    .map((group) => {
      const file = group[0];
      return `<article class="group"><h3>${escapeHtml(file.name)} • ${formatBytes(file.size)} • ${group.length} kopieën</h3>${group
        .map(
          (item) => `<p><strong>Schijf:</strong> ${escapeHtml(item.source)}<br/><span class="path">${escapeHtml(item.fullPath)}</span><br/><button class="delete-item" data-id="${item.id}">Opruimen</button></p>`,
        )
        .join("")}</article>`;
    })
    .join("");
}

function renderFolders(rows) {
  if (rows.length === 0) return "<p>Geen mappen beschikbaar.</p>";
  const map = new Map();
  rows.forEach((file) => {
    const list = map.get(file.folderPath) || [];
    list.push(file);
    map.set(file.folderPath, list);
  });
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b, "nl"))
    .map(
      ([folder, files]) => `<article class="group"><h3>${escapeHtml(folder)}</h3><p>${files.length} bestanden • ${formatBytes(files.reduce((s, f) => s + f.size, 0))}</p><p class="path">Bronnen: ${[...new Set(files.map((f) => f.source))].map(escapeHtml).join(", ")}</p></article>`,
    )
    .join("");
}

function buildForensicReport(files) {
  if (!files.length) return "<p>Geen scanresultaten beschikbaar voor analyse.</p>";
  const sortedByDate = [...files].sort((a, b) => new Date(a.lastModified) - new Date(b.lastModified));
  const duplicates = countDuplicateItems(files);
  const large = files.filter((f) => f.isLarge).length;
  const totalSize = files.reduce((s, f) => s + f.size, 0);

  const personProfiles = PERSONS.map((person) => {
    const mentions = files.filter((f) => `${f.name} ${f.fullPath} ${f.excerpt}`.toLowerCase().includes(person.toLowerCase()));
    return `<article class="group"><h4>${person}</h4><p>🟢 [FEIT] Vermeldingen in bestanden: ${mentions.length}.</p><p>🟡 [INTERPRETATIE] Documentconcentratie rond ${person} kan wijzen op dossierfocus in de geselecteerde bronset.</p><p>🔵 [NUANCERING] Vermelding in bestandsnaam of pad bewijst geen inhoudelijke betrokkenheid zonder inhoudscontrole.</p><p>🔴 [VERDRAAIING] Geen vastgesteld op basis van huidige metadata-scan.</p></article>`;
  }).join('');

  const evidenceRows = files.slice(0, 120).map((f, idx) => {
    const id = `B-${String(idx + 1).padStart(4, '0')}`;
    const relevance = f.isLarge || f.excerpt ? 'middel' : 'laag';
    return `<tr><td>${id}</td><td>${escapeHtml(f.name)}</td><td>${escapeHtml(f.type || extensionOf(f.name))}</td><td>${formatDate(f.lastModified)}</td><td class="path">${escapeHtml(f.fullPath)}</td><td>${relevance}</td></tr>`;
  }).join('');

  const timelineRows = sortedByDate.slice(0, 80).map((f) => `<li><strong>${formatDate(f.lastModified)}</strong> — ${escapeHtml(f.name)} (${escapeHtml(f.source)})</li>`).join('');

  return `
    <article class="group"><h3>Dossieroverzicht</h3><p>🟢 [FEIT] Gescande bestanden: ${files.length}. Dubbele bestanden: ${duplicates}. Rode bestanden: ${large}. Totale omvang: ${formatBytes(totalSize)}.</p></article>
    <article class="group"><h3>Personen & Rollen</h3>${personProfiles}</article>
    <article class="group"><h3>Chronologie</h3><ul>${timelineRows}</ul></article>
    <article class="group"><h3>Feiten vs Meningen</h3><p>🟢 [FEIT] Overzicht gebaseerd op bestandsmetadata en beperkte tekst-extractie.</p><p>🟡 [INTERPRETATIE] Narratiefverschuiving vereist inhoudelijke vergelijking van versies en tijdstempels.</p><p>🔵 [NUANCERING] Metadata toont aanwezigheid, niet de juridische waarde op zichzelf.</p><p>🔴 [VERDRAAIING] Niet geconstateerd zonder tegenstrijdige broninhoud.</p></article>
    <article class="group"><h3>Gedragsanalyse per persoon</h3><p>🟢 [FEIT] Analysepunt per persoon opgenomen op basis van vindplaatsen.</p><p>🟡 [INTERPRETATIE] Patronen in duplicaten en versie-aantallen kunnen wijzen op narratiefbeheer.</p></article>
    <article class="group"><h3>Inconsistenties & Verdraaiingen</h3><p>🟢 [FEIT] Duplicaatclusters met identieke naam+grootte gemarkeerd.</p><p>🟡 [INTERPRETATIE] Verspreiding over meerdere bronnen kan operationele backup zijn of selectieve verspreiding.</p></article>
    <article class="group"><h3>Juridische relevantie</h3><p>🟢 [FEIT] Bestandspaden, datums en grootte zijn direct verifieerbaar voor chain-of-custody voorbereiding.</p></article>
    <article class="group"><h3>Risico’s bij framing of misbruik</h3><p>🔵 [NUANCERING] Metadata-only conclusies mogen niet als inhoudelijk bewijs worden gepresenteerd zonder documentinhoud.</p></article>
    <article class="group"><h3>Samenvatting voor advocaat / rechter</h3><p>🟢 [FEIT] De scan levert een reproduceerbare catalogus met bronpad, omvang en tijdstempel.</p><p>🟡 [INTERPRETATIE] Prioriteit ligt bij dossierstukken in duplicaatclusters en rode bestanden.</p></article>
    <article class="group"><h3>Actieve dossierstatus</h3><p>Actief — laatst bijgewerkt op ${formatDate(new Date().toISOString())}.</p></article>
    <article class="group"><h3>Bewijsindex</h3><table class="table"><thead><tr><th>Bewijs-ID</th><th>Bestand</th><th>Type</th><th>Datum</th><th>Bronpad</th><th>Bewijskracht</th></tr></thead><tbody>${evidenceRows}</tbody></table></article>
    <article class="group"><h3>Tegenpartij-simulator</h3><p><strong>Scenario 1:</strong> Tegenpartij stelt dat duplicaten normale backups zijn. <br/>Tegenargument: tijdlijn en bronverschillen per duplicaatgroep tonen selectiepatroon.</p><p><strong>Scenario 2:</strong> Tegenpartij betwist herkomst. <br/>Tegenargument: volledige bronpaden en scanmomenten zijn vastgelegd in catalogus.</p><p><strong>Scenario 3:</strong> Tegenpartij minimaliseert grote bestanden als irrelevante media. <br/>Tegenargument: rode bestanden prioriteren op omvang en mogelijke informatiedichtheid.</p></article>
    <article class="group"><h3>AVG / GBA-toets</h3><p>🟢 [FEIT] Persoonsgegevens kunnen voorkomen in bestandsnamen/paden; verwerking gebeurt lokaal in browseropslag.</p><p>🔵 [NUANCERING] Verwerkingsgrondslag moet per zaak worden vastgelegd (gerechtvaardigd belang, juridische verplichting of rechtsvordering).</p></article>
  `;
}

function bindDeleteButtons() {
  document.querySelectorAll(".delete-item").forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.dataset.id;
      state.files = state.files.filter((file) => file.id !== id);
      persistCatalog();
      renderAll();
    });
  });
}

function countDuplicateItems(files) {
  const counts = new Map();
  files.forEach((file) => {
    counts.set(file.duplicateKey, (counts.get(file.duplicateKey) || 0) + 1);
  });
  let total = 0;
  counts.forEach((count) => {
    if (count > 1) total += count;
  });
  return total;
}

function pause(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function fingerprintOf(file) {
  return `${file.fullPath}|${file.size}|${file.lastModified}`;
}

function dedupeByFingerprint(files) {
  const seen = new Set();
  return files.filter((file) => {
    const fp = fingerprintOf(file);
    if (seen.has(fp)) return false;
    seen.add(fp);
    return true;
  });
}

function persistCatalog() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.files));
}

function loadCatalog() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed;
  } catch {
    return [];
  }
}

function extensionOf(filename) {
  const parts = filename.split('.');
  return parts.length > 1 ? parts.pop().toLowerCase() : 'onbekend';
}

async function safeExcerpt(file) {
  const ext = extensionOf(file.name);
  if (!["txt", "json", "csv", "html", "htm", "md"].includes(ext)) return "";
  try {
    const text = await file.text();
    return text.slice(0, 700);
  } catch {
    return "";
  }
}

function formatDate(isoValue) {
  return new Date(isoValue).toLocaleString("nl-NL");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  const exp = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exp;
  return `${value.toFixed(value >= 10 || exp === 0 ? 0 : 1)} ${units[exp]}`;
}
