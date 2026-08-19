// OQP Studio frontend — Phase 0 preview.
// Submits an .oqp input to the local backend, tails the job log, and links
// finished output files into the vendored OpenqpView results viewer.
// Phase 1 replaces this page with the full builder (Ketcher, Mol*, templates).

const DEFAULT_INPUT = `[input]
system=
 O   0.000   0.000   0.117
 H   0.000   0.755  -0.469
 H   0.000  -0.755  -0.469
charge=0
method=hf
basis=6-31g(d)
runtype=energy

[guess]
type=huckel

[scf]
type=rhf
maxit=50
`;

// Extensions OpenqpView can open via its ?load= parameter.
const VIEWABLE = [".log", ".txt", ".json", ".molden", ".cube", ".cub", ".xyz"];

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const input = $<HTMLTextAreaElement>("input");
const log = $<HTMLPreElement>("log");
const statusEl = $<HTMLSpanElement>("status");
const runnerSelect = $<HTMLSelectElement>("runner");
const filesList = $<HTMLUListElement>("files");

input.value = DEFAULT_INPUT;

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
  const firstAvailable = Object.entries(runners).find(([, ok]) => ok)?.[0];
  if (firstAvailable) runnerSelect.value = firstAvailable;
}

async function showFiles(jobId: string): Promise<void> {
  const files: { name: string; size: number }[] = await (
    await fetch(`/api/jobs/${jobId}/files`)
  ).json();
  filesList.innerHTML = "";
  for (const f of files) {
    const li = document.createElement("li");
    const url = `/api/jobs/${jobId}/files/${encodeURIComponent(f.name)}`;
    const viewable = VIEWABLE.some((ext) => f.name.toLowerCase().endsWith(ext));
    li.innerHTML = viewable
      ? `${f.name} (${f.size} B) — <a href="/viewer/index.html?load=${encodeURIComponent(url)}"
           target="_blank">open in viewer</a> · <a href="${url}" download>download</a>`
      : `${f.name} (${f.size} B) — <a href="${url}" download>download</a>`;
    filesList.appendChild(li);
  }
}

async function poll(jobId: string): Promise<void> {
  const info = await (await fetch(`/api/jobs/${jobId}`)).json();
  const tail = await (await fetch(`/api/jobs/${jobId}/log`)).json();
  log.textContent = tail.log || "(no output yet)";
  statusEl.textContent = info.status + (info.error ? ` — ${info.error}` : "");
  if (info.status === "queued" || info.status === "running") {
    setTimeout(() => poll(jobId), 1000);
  } else {
    showFiles(jobId);
  }
}

$<HTMLButtonElement>("run").addEventListener("click", async () => {
  statusEl.textContent = "submitting…";
  filesList.innerHTML = "";
  const res = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input_text: input.value, runner: runnerSelect.value || "local" }),
  });
  if (!res.ok) {
    statusEl.textContent = `submit failed (${res.status})`;
    return;
  }
  const job = await res.json();
  poll(job.id);
});

loadRunners().catch(() => {
  statusEl.textContent = "backend not reachable — start it on port 8814";
});
