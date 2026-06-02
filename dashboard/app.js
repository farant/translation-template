async function load() {
  const res = await fetch("/api/status");
  const data = await res.json();
  renderChecks(data.checks);
  renderWorks(data.works);
}

function renderChecks(checks) {
  const tbody = document.querySelector("#checks tbody");
  tbody.innerHTML = "";
  for (const c of checks) {
    const tr = document.createElement("tr");
    const status = c.installed
      ? `<span class="ok">&#10003; ${c.version || "installed"}</span>`
      : `<span class="missing">&#10007; missing</span>`;
    const install = c.installed ? "" : `<code>${c.install}</code>`;
    tr.innerHTML = `<td>${c.name}</td><td>${c.purpose}</td><td>${status}</td><td>${install}</td>`;
    tbody.appendChild(tr);
  }
}

function renderWorks(works) {
  const box = document.querySelector("#works");
  box.innerHTML = "";
  if (!works.length) {
    box.innerHTML = "<p>No works yet. Drop a PDF in <code>source/</code> and tell Claude “let’s get started.”</p>";
    return;
  }
  const order = ["ingest", "transcribe", "translate", "build_html", "publish"];
  for (const w of works) {
    const done = order.filter((s) => w.stages[s] && w.stages[s].done).length;
    const pct = Math.round((done / order.length) * 100);
    const stages = order
      .map((s) => `<span class="stage ${w.stages[s] && w.stages[s].done ? "done" : "pending"}">${s}</span>`)
      .join("");
    const div = document.createElement("div");
    div.className = "work";
    div.innerHTML =
      `<strong>${w.title || w.work}</strong> &middot; <span>${w.ocr_method || ""}</span><br />` +
      `<span class="bar"><span style="width:${pct}%"></span></span> ${done}/${order.length}<br />${stages}`;
    box.appendChild(div);
  }
}

load();
