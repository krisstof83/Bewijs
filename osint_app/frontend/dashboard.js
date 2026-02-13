const API = "http://localhost:8000";

function setTabs() {
  const buttons = document.querySelectorAll(".tabs button");
  const sections = document.querySelectorAll(".tab-content");
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      sections.forEach((s) => s.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(button.dataset.tab).classList.add("active");
    });
  });
}

async function loadSummary() {
  const data = await fetch(`${API}/dashboard/summary`).then((r) => r.json());
  document.getElementById("summary-cards").innerHTML = `
    <article><h3>Total Evidence</h3><p>${data.total_evidence}</p></article>
    <article><h3>Total Dossiers</h3><p>${data.total_dossiers}</p></article>
    <article><h3>High Relevance</h3><p>${data.high_relevance_evidence}</p></article>
  `;
}

async function loadEvidence() {
  const data = await fetch(`${API}/evidence/list`).then((r) => r.json());
  document.getElementById("evidence-list").innerHTML = data
    .map(
      (item) =>
        `<li><strong>${item.detected_person}</strong> • ${item.detected_case}<br/><small>${item.file_path}</small></li>`,
    )
    .join("");
}

async function loadTimeline() {
  const data = await fetch(`${API}/timeline`).then((r) => r.json());
  document.getElementById("timeline-list").innerHTML = data
    .slice(-40)
    .map((event) => `<li><strong>${event.timestamp}</strong> — ${event.title}</li>`)
    .join("");
}

function setOsintForm() {
  const form = document.getElementById("osint-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = document.getElementById("q").value;
    const payload = { query, filters: {} };
    const data = await fetch(`${API}/osint/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then((r) => r.json());

    document.getElementById("osint-list").innerHTML = data
      .map((item) => `<li><a href="${item.url}" target="_blank">${item.source}</a>: ${item.title}</li>`)
      .join("");
  });
}

async function refreshAll() {
  await Promise.all([loadSummary(), loadEvidence(), loadTimeline()]);
}

setTabs();
setOsintForm();
refreshAll();
setInterval(refreshAll, 30000);
