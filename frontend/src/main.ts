// OQP Studio frontend — Phase 0 preview.
// Submits an .oqp input to the local backend and tails the job log.
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

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const input = $<HTMLTextAreaElement>("input");
const log = $<HTMLPreElement>("log");
const statusEl = $<HTMLSpanElement>("status");

input.value = DEFAULT_INPUT;

async function poll(jobId: string): Promise<void> {
  const info = await (await fetch(`/api/jobs/${jobId}`)).json();
  const tail = await (await fetch(`/api/jobs/${jobId}/log`)).json();
  log.textContent = tail.log || "(no output yet)";
  statusEl.textContent = info.status + (info.error ? ` — ${info.error}` : "");
  if (info.status === "queued" || info.status === "running") {
    setTimeout(() => poll(jobId), 1000);
  }
}

$<HTMLButtonElement>("run").addEventListener("click", async () => {
  statusEl.textContent = "submitting…";
  const res = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input_text: input.value, runner: "local" }),
  });
  if (!res.ok) {
    statusEl.textContent = `submit failed (${res.status})`;
    return;
  }
  const job = await res.json();
  poll(job.id);
});
