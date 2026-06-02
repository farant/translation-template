const frame = document.getElementById("frame");
const scan = document.getElementById("scan");
const workSel = document.getElementById("work");
const latin = document.getElementById("latin");

let currentWork = null;

async function init() {
  const works = await (await fetch("/api/works")).json();
  workSel.innerHTML = works
    .map((w) => `<option value="${w.name}" data-latin="${w.has_latin}">${w.name}</option>`)
    .join("");
  workSel.addEventListener("change", loadWork);
  latin.addEventListener("change", loadWork);
  if (works.length) loadWork();
}

function loadWork() {
  currentWork = workSel.value;
  const opt = workSel.selectedOptions[0];
  const wantLatin = latin.checked && opt && opt.dataset.latin === "true";
  const suffix = wantLatin ? "_la" : "";
  frame.src = `/output/${currentWork}${suffix}.html`;
}

frame.addEventListener("load", wireFrame);

function wireFrame() {
  const doc = frame.contentDocument;
  if (!doc) return;
  const blocks = Array.from(doc.querySelectorAll("[data-page]"));
  blocks.forEach((el, index) => {
    el.style.cursor = "pointer";
    el.addEventListener("click", () => showPage(el.dataset.page));
    const flag = doc.createElement("button");
    flag.textContent = "⚑";
    flag.title = "Flag an issue here";
    flag.style.cssText = "margin-left:.4rem;border:0;background:none;cursor:pointer;color:#b3261e;";
    flag.addEventListener("click", (e) => {
      e.stopPropagation();
      const note = doc.defaultView.prompt("What's wrong with this block?");
      if (note) sendFlag(el.dataset.page, index, note, flag);
    });
    el.appendChild(flag);
  });
}

function showPage(page) {
  scan.src = `/pages/${currentWork}/pages/page-${page}.png`;
}

async function sendFlag(page, block, note, btn) {
  await fetch("/api/flag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ work: currentWork, page, block, note }),
  });
  btn.textContent = "✓";
  btn.style.color = "#1a7f37";
}

init();
