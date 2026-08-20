// OQP Studio frontend — Builder → Method → Run → Results workflow.
// Vanilla TS for now; Phase 1/2 swap the preview canvas for Mol* and add
// the Ketcher sketcher and keyword-schema forms.

type Atom = [string, number, number, number];

const SAMPLES: Record<string, Atom[]> = {
  water: [
    ["O", 0.0, 0.0, 0.117],
    ["H", 0.0, 0.755, -0.469],
    ["H", 0.0, -0.755, -0.469],
  ],
  ethanol: [
    ["C", -1.0, 0.0, 0.0], ["C", 0.45, 0.0, 0.0], ["O", 1.55, 0.74, 0.0],
    ["H", -1.38, -1.0, 0.0], ["H", -1.38, 0.5, 0.88], ["H", -1.38, 0.5, -0.88],
    ["H", 0.74, -0.55, 0.88], ["H", 0.74, -0.55, -0.88], ["H", 2.32, 0.18, 0.0],
  ],
  benzene: [
    ["C", 1.4, 0.0, 0.0], ["C", 0.7, 1.21, 0.0], ["C", -0.7, 1.21, 0.0],
    ["C", -1.4, 0.0, 0.0], ["C", -0.7, -1.21, 0.0], ["C", 0.7, -1.21, 0.0],
    ["H", 2.48, 0.0, 0.0], ["H", 1.24, 2.15, 0.0], ["H", -1.24, 2.15, 0.0],
    ["H", -2.48, 0.0, 0.0], ["H", -1.24, -2.15, 0.0], ["H", 1.24, -2.15, 0.0],
  ],
};

const VIEWABLE = [".log", ".txt", ".json", ".molden", ".cube", ".cub", ".xyz"];

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

// ---------- tabs ----------
const nav = $<HTMLElement>("nav");
function showTab(name: string): void {
  document.querySelectorAll<HTMLElement>(".panel").forEach((p) => {
    p.classList.toggle("active", p.id === `panel-${name}`);
  });
  nav.querySelectorAll("button").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === name);
  });
  if (name === "results") refreshJobs();
  if (name === "method") updateInpPreview();
}
nav.addEventListener("click", (e) => {
  const btn = (e.target as HTMLElement).closest("button");
  if (btn?.dataset.tab) showTab(btn.dataset.tab);
});

// ---------- builder ----------
const xyzArea = $<HTMLTextAreaElement>("xyz");
const builderStatus = $<HTMLSpanElement>("builderStatus");

function atomsToText(atoms: Atom[]): string {
  return atoms
    .map(([el, x, y, z]) =>
      `${el.padEnd(2)} ${x.toFixed(6).padStart(11)} ${y.toFixed(6).padStart(11)} ${z.toFixed(6).padStart(11)}`)
    .join("\n");
}

function parseAtoms(text: string): Atom[] {
  const atoms: Atom[] = [];
  for (const raw of text.split("\n")) {
    const parts = raw.trim().split(/\s+/);
    if (parts.length < 4) continue;
    const [el, x, y, z] = [parts[0], +parts[1], +parts[2], +parts[3]];
    if (/^[A-Za-z]{1,2}$/.test(el) && [x, y, z].every(Number.isFinite)) {
      atoms.push([el, x, y, z]);
    }
  }
  return atoms;
}

$<HTMLSelectElement>("sample").addEventListener("change", (e) => {
  const key = (e.target as HTMLSelectElement).value;
  if (SAMPLES[key]) {
    xyzArea.value = atomsToText(SAMPLES[key]);
    updatePreview();
  }
});

$<HTMLButtonElement>("pubchemFetch").addEventListener("click", async () => {
  const name = $<HTMLInputElement>("pubchemName").value.trim();
  if (!name) return;
  builderStatus.textContent = `searching PubChem for “${name}”…`;
  try {
    const res = await fetch(`/api/pubchem/${encodeURIComponent(name)}`);
    if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
    const data = await res.json();
    xyzArea.value = atomsToText(data.atoms);
    builderStatus.textContent = `${data.atoms.length} atoms loaded from PubChem`;
    updatePreview();
  } catch (err) {
    builderStatus.textContent = `PubChem: ${(err as Error).message}`;
  }
});

async function updatePreview(): Promise<void> {
  const atoms = parseAtoms(xyzArea.value);
  if (!atoms.length) return;
  const xyz = `${atoms.length}\nOQP Studio preview\n${atomsToText(atoms)}\n`;
  const res = await fetch("/api/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ xyz }),
  });
  if (!res.ok) return;
  const { url } = await res.json();
  $<HTMLIFrameElement>("previewFrame").src =
    `/builder3d.html?load=${encodeURIComponent(url)}`;
}
$<HTMLButtonElement>("previewBtn").addEventListener("click", updatePreview);

// ---------- method: workflow catalog ----------
// First pick a workflow (like app.openqp.org); details open on demand.
interface Workflow {
  key: string;
  title: string;
  desc: string;
  mrsfOnly?: boolean;   // enforces the MRSF-TDDFT route
  defaultTheory?: string;
}

const WORKFLOWS: Workflow[] = [
  { key: "energy", title: "Single-point energy", desc: "HF / DFT / MP2 / MRSF energy at the given geometry", defaultTheory: "dft" },
  { key: "opt", title: "Geometry optimization", desc: "Minimize the ground- or excited-state structure", defaultTheory: "dft" },
  { key: "hess", title: "Frequencies (Hessian)", desc: "Vibrational frequencies, IR; thermochemistry", defaultTheory: "dft" },
  { key: "abs", title: "Absorption spectrum", desc: "MRSF-TDDFT vertical excitation energies", mrsfOnly: true },
  { key: "exgrad", title: "Excited-state gradient", desc: "MRSF-TDDFT gradient of a chosen state", mrsfOnly: true },
  { key: "exopt", title: "Excited-state optimization", desc: "Optimize S1 or another MRSF state", mrsfOnly: true },
  { key: "meci", title: "MECI search", desc: "Minimum-energy conical intersection between two states", mrsfOnly: true },
  { key: "soc", title: "Spin–orbit coupling", desc: "MRSF-TDDFT SOC between singlets and triplets", mrsfOnly: true },
  { key: "ekt", title: "Ionization / EA (EKT)", desc: "MRSF extended-Koopmans IP and EA with Dyson orbitals", mrsfOnly: true },
];

let currentWf: Workflow = WORKFLOWS[0];

const theorySel = $<HTMLSelectElement>("theory");
const functionalInp = $<HTMLInputElement>("functional");
const basisSel = $<HTMLSelectElement>("basis");
const basisCustom = $<HTMLInputElement>("basisCustom");
const optionsCard = $<HTMLDivElement>("optionsCard");

function selectWorkflow(wf: Workflow): void {
  currentWf = wf;
  document.querySelectorAll<HTMLElement>(".wf-card").forEach((c) => {
    c.classList.toggle("sel", c.dataset.key === wf.key);
  });
  document.querySelectorAll<HTMLElement>(".wf-opt").forEach((row) => {
    row.classList.toggle("on", (row.dataset.for ?? "").split(" ").includes(wf.key));
  });
  if (wf.mrsfOnly) {
    theorySel.value = "mrsf";
    theorySel.disabled = true;
  } else {
    theorySel.disabled = false;
    if (theorySel.value === "mrsf" || !theorySel.value) {
      theorySel.value = wf.defaultTheory ?? "dft";
    }
  }
  $<HTMLSpanElement>("wfLabel").textContent = `— ${wf.title}`;
  optionsCard.style.display = "";
  syncFieldStates();
  updateInpPreview();
}

function buildWorkflowGrid(): void {
  const grid = $<HTMLDivElement>("wfGrid");
  for (const wf of WORKFLOWS) {
    const card = document.createElement("div");
    card.className = "wf-card";
    card.dataset.key = wf.key;
    card.innerHTML = `<div class="wf-title">${wf.title}</div><div class="wf-desc">${wf.desc}</div>`;
    card.addEventListener("click", () => selectWorkflow(wf));
    grid.appendChild(card);
  }
}

function currentBasis(): string {
  return basisSel.value === "__custom__" ? basisCustom.value.trim() : basisSel.value;
}

// Generates concise .oqp input: ROUTE, one primary driver, globals, geometry.
function generateInp(): string {
  const atoms = parseAtoms(xyzArea.value);
  const theory = currentWf.mrsfOnly ? "mrsf" : theorySel.value;
  const charge = +$<HTMLInputElement>("charge").value || 0;
  const mult = +$<HTMLInputElement>("mult").value || 1;
  const nstate = +$<HTMLInputElement>("nstate").value || 3;
  const target = +$<HTMLInputElement>("targetState").value || 0;
  const basis = currentBasis();
  const functional = functionalInp.value.trim() || "bhhlyp";

  const routes: Record<string, string> = {
    hf: `hf/${basis}`,
    dft: `dft/${functional}/${basis}`,
    mp2: `mp2/${basis}`,
    tddft: `tddft(nstate=${nstate})/${functional}/${basis}`,
    mrsf: `mrsf(nstate=${nstate})/${functional}/${basis}`,
  };

  const usesStates = theory === "tddft" || theory === "mrsf";
  const stateArg = usesStates && target > 0 ? `(S${target})` : "";
  let driver: string;
  switch (currentWf.key) {
    case "energy": driver = `energy${stateArg}`; break;
    case "opt": driver = `opt${stateArg}`; break;
    case "hess": driver = `hess${stateArg}`; break;
    case "abs": driver = "energy"; break;
    case "exgrad": driver = `grad(S${target || 1})`; break;
    case "exopt": driver = `opt(S${target || 1})`; break;
    case "meci": {
      const a = +$<HTMLInputElement>("meciA").value || 0;
      const b = +$<HTMLInputElement>("meciB").value || 1;
      driver = `meci(S${Math.min(a, b)},S${Math.max(a, b)})`;
      break;
    }
    case "soc": driver = "soc"; break;
    case "ekt": {
      const opts = [];
      if ($<HTMLInputElement>("ektIp").checked) opts.push("ip=true");
      if ($<HTMLInputElement>("ektEa").checked) opts.push("ea=true");
      driver = `ekt(${opts.join(",") || "ip=true"})`;
      break;
    }
    default: driver = "energy";
  }

  const lines: string[] = [routes[theory], driver];
  if (charge !== 0) lines.push(`charge=${charge}`);
  // MRSF selects its high-spin working reference automatically — no mult.
  if (mult !== 1 && theory !== "mrsf") lines.push(`mult=${mult}`);
  lines.push('geom="""');
  for (const [el, x, y, z] of atoms) {
    lines.push(`${el.padEnd(2)} ${x.toFixed(6).padStart(11)} ${y.toFixed(6).padStart(11)} ${z.toFixed(6).padStart(11)}`);
  }
  lines.push('"""');
  return lines.join("\n") + "\n";
}

function updateInpPreview(): void {
  $<HTMLPreElement>("inpPreview").textContent = generateInp();
}
function syncFieldStates(): void {
  functionalInp.disabled =
    !theorySel.disabled && (theorySel.value === "hf" || theorySel.value === "mp2");
  basisCustom.disabled = basisSel.value !== "__custom__";
}

for (const id of ["theory", "functional", "basis", "basisCustom", "charge", "mult",
                  "nstate", "targetState", "meciA", "meciB", "ektIp", "ektEa"]) {
  $<HTMLElement>(id).addEventListener("input", () => {
    syncFieldStates();
    updateInpPreview();
  });
}

$<HTMLButtonElement>("generate").addEventListener("click", () => {
  $<HTMLTextAreaElement>("input").value = generateInp();
  showTab("run");
});

// ---------- run ----------
const runStatus = $<HTMLSpanElement>("runStatus");
const runLog = $<HTMLPreElement>("runLog");
const runnerSelect = $<HTMLSelectElement>("runner");

async function loadRunners(): Promise<void> {
  const runners: Record<string, boolean> = await (await fetch("/api/runners")).json();
  runnerSelect.innerHTML = "";
  for (const [name, available] of Object.entries(runners)) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = available ? name : `${name} (unavailable)`;
    opt.disabled = !available;
    runnerSelect.appendChild(opt);
  }
  const first = Object.entries(runners).find(([, ok]) => ok)?.[0];
  if (first) runnerSelect.value = first;
  $<HTMLSpanElement>("runnersInfo").textContent =
    "runners: " + Object.entries(runners).map(([n, ok]) => `${n} ${ok ? "✓" : "✗"}`).join(" · ");
}

async function pollJob(jobId: string): Promise<void> {
  const info = await (await fetch(`/api/jobs/${jobId}`)).json();
  const tail = await (await fetch(`/api/jobs/${jobId}/log`)).json();
  runLog.textContent = tail.log || "(no output yet)";
  runStatus.textContent = info.status + (info.error ? ` — ${info.error}` : "");
  if (info.status === "queued" || info.status === "running") {
    setTimeout(() => pollJob(jobId), 1000);
  } else {
    selectJob(jobId);
  }
}

$<HTMLButtonElement>("runBtn").addEventListener("click", async () => {
  runStatus.textContent = "submitting…";
  const res = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      input_text: $<HTMLTextAreaElement>("input").value,
      runner: runnerSelect.value || "local",
    }),
  });
  if (!res.ok) {
    runStatus.textContent = `submit failed (${res.status})`;
    return;
  }
  pollJob((await res.json()).id);
});

// ---------- results ----------
let selectedJob = "";

async function refreshJobs(): Promise<void> {
  const jobs: { id: string; runner: string; status: string }[] =
    await (await fetch("/api/jobs")).json();
  const body = $<HTMLTableSectionElement>("jobsBody");
  body.innerHTML = "";
  for (const job of jobs) {
    const tr = document.createElement("tr");
    if (job.id === selectedJob) tr.className = "sel";
    tr.innerHTML =
      `<td>${job.id}</td><td>${job.runner}</td>` +
      `<td><span class="badge ${job.status}">${job.status}</span></td>`;
    tr.addEventListener("click", () => selectJob(job.id));
    body.appendChild(tr);
  }
}
$<HTMLButtonElement>("jobsRefresh").addEventListener("click", refreshJobs);

async function selectJob(jobId: string): Promise<void> {
  selectedJob = jobId;
  refreshJobs();
  const files: { name: string; size: number }[] =
    await (await fetch(`/api/jobs/${jobId}/files`)).json();
  const list = $<HTMLUListElement>("resultFiles");
  list.innerHTML = files.length ? "" : '<li class="hint">no files</li>';
  for (const f of files) {
    const url = `/api/jobs/${jobId}/files/${encodeURIComponent(f.name)}`;
    const li = document.createElement("li");
    const viewable = VIEWABLE.some((ext) => f.name.toLowerCase().endsWith(ext));
    li.innerHTML =
      `${f.name} <span class="hint">(${f.size.toLocaleString()} B)</span>` +
      (viewable ? ` <a href="#" data-url="${url}" data-name="${f.name}">view</a>` : "") +
      ` <a href="${url}" download>download</a>`;
    list.appendChild(li);
  }
  list.querySelectorAll<HTMLAnchorElement>("a[data-url]").forEach((a) => {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      viewResultFile(jobId, a.dataset.name!, a.dataset.url!);
    });
  });
}

const resultFrame = $<HTMLIFrameElement>("resultFrame");
const orbitalCard = $<HTMLDivElement>("orbitalCard");
const orbitalSel = $<HTMLSelectElement>("orbitalSel");
const isoRange = $<HTMLInputElement>("isoRange");
let currentMolden: { jobId: string; name: string } | null = null;

// Mol* renders geometries and cube/orbital isosurfaces; other formats
// (logs, hessian JSON) fall back to the classic embedded viewer.
async function viewResultFile(jobId: string, name: string, url: string): Promise<void> {
  const lower = name.toLowerCase();
  orbitalCard.style.display = "none";
  currentMolden = null;
  if (lower.endsWith(".xyz")) {
    resultFrame.src = `/builder3d.html?load=${encodeURIComponent(url)}`;
  } else if (lower.endsWith(".cube") || lower.endsWith(".cub")) {
    resultFrame.src = `/builder3d.html?cube=${encodeURIComponent(url)}`;
  } else if (lower.endsWith(".molden")) {
    const base = `/api/jobs/${jobId}/molden/${encodeURIComponent(name)}`;
    const res = await fetch(`${base}/orbitals`);
    if (!res.ok) {
      // Spherical-harmonic basis etc. — classic viewer still handles it.
      resultFrame.src = `/viewer/index.html?load=${encodeURIComponent(url)}`;
      return;
    }
    const data = await res.json();
    currentMolden = { jobId, name };
    orbitalSel.innerHTML = "";
    for (const o of data.orbitals) {
      const opt = document.createElement("option");
      opt.value = String(o.index);
      const occ = o.occupancy != null ? ` occ=${o.occupancy}` : "";
      opt.textContent = `MO ${o.index}  E=${o.energy.toFixed(4)} Ha${occ} ${o.spin}`;
      orbitalSel.appendChild(opt);
    }
    // Start at the highest (partially) occupied orbital when known.
    const homo = [...data.orbitals].reverse().find((o: { occupancy: number | null }) =>
      (o.occupancy ?? 0) > 1e-6);
    if (homo) orbitalSel.value = String(homo.index);
    orbitalCard.style.display = "";
    showOrbital();
  } else {
    resultFrame.src = `/viewer/index.html?load=${encodeURIComponent(url)}`;
  }
}

function showOrbital(): void {
  if (!currentMolden) return;
  const base = `/api/jobs/${currentMolden.jobId}/molden/${encodeURIComponent(currentMolden.name)}`;
  const geom = `${base}/geom.xyz`;
  const cube = `${base}/cube?mo=${orbitalSel.value}`;
  resultFrame.src =
    `/builder3d.html?load=${encodeURIComponent(geom)}` +
    `&cube=${encodeURIComponent(cube)}&iso=${isoRange.value}`;
}
orbitalSel.addEventListener("change", showOrbital);
isoRange.addEventListener("change", showOrbital);

// ---------- boot ----------
xyzArea.value = atomsToText(SAMPLES.water);
buildWorkflowGrid();
selectWorkflow(WORKFLOWS[0]);
fetch("/api/health")
  .then((r) => r.json())
  .then((h) => { $<HTMLSpanElement>("health").textContent = `backend: v${h.version} ✓`; })
  .catch(() => { $<HTMLSpanElement>("health").textContent = "backend: not reachable (start it on port 8814)"; });
loadRunners().catch(() => {});
updatePreview().catch(() => {});
