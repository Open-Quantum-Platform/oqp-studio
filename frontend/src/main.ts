// OQP Studio frontend — Builder → Method → Run → Results workflow.
// Vanilla TS for now; Phase 1/2 swap the preview canvas for Mol* and add
// the Ketcher sketcher and keyword-schema forms.

type Atom = [string, number, number, number];

// Geometries generated with RDKit ETKDGv3 + MMFF94 (seed 0xF00D).
const SAMPLES: Record<string, { label: string; atoms: Atom[] }> = {
  water: { label: "Water (H₂O)", atoms: [["O",0.001,0.398,0.000],["H",-0.764,-0.197,0.000],["H",0.763,-0.201,0.000]] },
  ammonia: { label: "Ammonia (NH₃)", atoms: [["N",0.021,-0.007,0.295],["H",0.916,-0.162,-0.168],["H",-0.612,-0.716,-0.073],["H",-0.325,0.886,-0.054]] },
  methane: { label: "Methane (CH₄)", atoms: [["C",-0.000,0.000,0.000],["H",-0.635,-0.826,-0.329],["H",-0.442,0.947,-0.316],["H",0.085,-0.017,1.089],["H",0.992,-0.105,-0.444]] },
  methanol: { label: "Methanol (CH₃OH)", atoms: [["C",-0.371,-0.013,0.018],["O",0.950,-0.078,0.525],["H",-1.074,-0.189,0.835],["H",-0.550,0.978,-0.407],["H",-0.506,-0.780,-0.748],["H",1.551,0.082,-0.222]] },
  ethanol: { label: "Ethanol (C₂H₅OH)", atoms: [["C",0.872,0.199,0.135],["C",-0.461,-0.516,0.045],["O",-1.326,0.182,-0.839],["H",0.739,1.219,0.511],["H",1.556,-0.335,0.800],["H",1.332,0.283,-0.855],["H",-0.939,-0.580,1.027],["H",-0.325,-1.530,-0.341],["H",-1.448,1.078,-0.483]] },
  formaldehyde: { label: "Formaldehyde (CH₂O)", atoms: [["C",-0.012,0.002,-0.001],["O",1.197,-0.164,0.098],["H",-0.718,-0.842,-0.050],["H",-0.467,1.004,-0.047]] },
  acetone: { label: "Acetone (C₃H₆O)", atoms: [["C",-1.269,-0.226,-0.089],["C",0.006,0.198,0.589],["O",0.017,0.591,1.754],["C",1.266,0.119,-0.230],["H",-1.190,-1.272,-0.395],["H",-1.450,0.410,-0.959],["H",-2.108,-0.123,0.605],["H",1.436,-0.915,-0.541],["H",1.176,0.767,-1.105],["H",2.117,0.452,0.371]] },
  aceticacid: { label: "Acetic acid (CH₃COOH)", atoms: [["C",-0.956,-0.066,0.101],["C",0.477,0.276,-0.141],["O",0.909,1.333,-0.567],["O",1.306,-0.738,0.169],["H",-1.109,-0.293,1.159],["H",-1.244,-0.916,-0.521],["H",-1.582,0.791,-0.166],["H",2.198,-0.386,-0.034]] },
  ethylene: { label: "Ethylene (C₂H₄)", atoms: [["C",0.570,0.134,-0.322],["C",-0.570,-0.134,0.322],["H",0.813,-0.359,-1.258],["H",1.281,0.852,0.075],["H",-1.281,-0.852,-0.075],["H",-0.813,0.359,1.258]] },
  acetylene: { label: "Acetylene (C₂H₂)", atoms: [["C",0.595,-0.007,-0.106],["C",-0.595,0.007,0.044],["H",1.653,-0.020,-0.239],["H",-1.653,0.020,0.177]] },
  butadiene: { label: "1,3-Butadiene (C₄H₆)", atoms: [["C",-1.607,0.846,-0.458],["C",-0.354,0.609,-0.053],["C",0.354,-0.609,-0.364],["C",1.607,-0.846,0.041],["H",-2.169,0.131,-1.049],["H",-2.101,1.778,-0.200],["H",0.163,1.362,0.539],["H",-0.163,-1.362,-0.955],["H",2.169,-0.131,0.633],["H",2.101,-1.778,-0.217]] },
  benzene: { label: "Benzene (C₆H₆)", atoms: [["C",-0.303,-1.361,-0.009],["C",-1.331,-0.418,0.015],["C",-1.027,0.943,0.024],["C",0.303,1.361,0.009],["C",1.331,0.418,-0.015],["C",1.027,-0.943,-0.024],["H",-0.539,-2.422,-0.016],["H",-2.367,-0.744,0.027],["H",-1.828,1.678,0.042],["H",0.539,2.422,0.016],["H",2.367,0.744,-0.027],["H",1.828,-1.678,-0.042]] },
  toluene: { label: "Toluene (C₇H₈)", atoms: [["C",2.221,0.034,-0.027],["C",0.721,0.010,-0.034],["C",0.031,-1.206,0.028],["C",-1.365,-1.227,0.054],["C",-2.081,-0.032,0.029],["C",-1.403,1.185,-0.018],["C",-0.007,1.206,-0.044],["H",2.590,0.071,1.002],["H",2.628,-0.856,-0.518],["H",2.600,0.906,-0.571],["H",0.577,-2.147,0.056],["H",-1.893,-2.176,0.097],["H",-3.168,-0.048,0.050],["H",-1.960,2.117,-0.032],["H",0.509,2.163,-0.073]] },
  phenol: { label: "Phenol (C₆H₅OH)", atoms: [["O",-2.475,0.279,0.115],["C",-1.120,0.140,0.058],["C",-0.341,1.202,0.503],["C",1.050,1.102,0.462],["C",1.651,-0.059,-0.023],["C",0.862,-1.121,-0.468],["C",-0.530,-1.024,-0.429],["H",-2.882,-0.534,-0.226],["H",-0.815,2.104,0.879],["H",1.663,1.930,0.809],["H",2.735,-0.137,-0.055],["H",1.333,-2.025,-0.846],["H",-1.131,-1.857,-0.778]] },
  aniline: { label: "Aniline (C₆H₅NH₂)", atoms: [["N",2.275,-0.456,0.086],["C",0.912,-0.153,-0.017],["C",0.023,-1.083,-0.562],["C",-1.353,-0.840,-0.564],["C",-1.856,0.320,0.020],["C",-0.984,1.226,0.620],["C",0.391,0.977,0.618],["H",2.867,0.362,0.190],["H",2.608,-1.084,-0.638],["H",0.396,-2.009,-0.992],["H",-2.031,-1.564,-1.007],["H",-2.926,0.508,0.025],["H",-1.373,2.118,1.102],["H",1.054,1.677,1.119]] },
  naphthalene: { label: "Naphthalene (C₁₀H₈)", atoms: [["C",2.427,0.669,0.269],["C",2.429,-0.710,0.077],["C",1.224,-1.391,-0.105],["C",0.001,-0.700,-0.098],["C",-1.220,-1.370,-0.279],["C",-2.427,-0.669,-0.269],["C",-2.429,0.710,-0.077],["C",-1.224,1.391,0.105],["C",-0.001,0.700,0.098],["C",1.220,1.370,0.280],["H",3.364,1.200,0.411],["H",3.368,-1.256,0.069],["H",1.246,-2.468,-0.253],["H",-1.238,-2.447,-0.431],["H",-3.364,-1.200,-0.412],["H",-3.368,1.256,-0.069],["H",-1.246,2.468,0.253],["H",1.238,2.447,0.431]] },
  anthracene: { label: "Anthracene (C₁₄H₁₀)", atoms: [["C",-3.660,0.660,-0.212],["C",-3.477,-0.147,-1.331],["C",-2.206,-0.636,-1.636],["C",-1.101,-0.324,-0.825],["C",0.184,-0.808,-1.120],["C",1.288,-0.495,-0.309],["C",2.573,-0.980,-0.602],["C",3.660,-0.660,0.212],["C",3.477,0.147,1.331],["C",2.206,0.636,1.636],["C",1.101,0.324,0.825],["C",-0.184,0.808,1.120],["C",-1.288,0.495,0.309],["C",-2.573,0.980,0.602],["H",-4.649,1.042,0.027],["H",-4.322,-0.397,-1.967],["H",-2.082,-1.266,-2.514],["H",0.328,-1.440,-1.994],["H",2.737,-1.612,-1.472],["H",4.649,-1.042,-0.027],["H",4.322,0.397,1.967],["H",2.082,1.266,2.514],["H",-0.328,1.440,1.994],["H",-2.737,1.612,1.472]] },
  pyridine: { label: "Pyridine (C₅H₅N)", atoms: [["C",-0.329,1.137,-0.014],["C",1.019,0.795,-0.050],["C",1.355,-0.549,-0.032],["N",0.448,-1.550,0.019],["C",-0.852,-1.187,0.053],["C",-1.286,0.129,0.039],["H",-0.631,2.180,-0.027],["H",1.789,1.557,-0.092],["H",2.393,-0.867,-0.059],["H",-1.561,-2.009,0.094],["H",-2.344,0.363,0.068]] },
  pyrrole: { label: "Pyrrole (C₄H₅N)", atoms: [["C",-1.069,0.511,-0.153],["C",-0.819,-0.869,0.034],["C",0.542,-1.025,0.170],["N",1.122,0.213,0.071],["C",0.147,1.156,-0.126],["H",-2.033,0.984,-0.293],["H",-1.553,-1.664,0.066],["H",1.146,-1.908,0.328],["H",2.114,0.401,0.133],["H",0.402,2.202,-0.230]] },
  furan: { label: "Furan (C₄H₄O)", atoms: [["C",0.567,-0.858,0.017],["C",-0.824,-0.611,-0.079],["C",-0.972,0.756,-0.050],["O",0.238,1.363,0.058],["C",1.170,0.376,0.098],["H",1.070,-1.814,0.026],["H",-1.620,-1.337,-0.160],["H",-1.825,1.419,-0.094],["H",2.196,0.706,0.185]] },
  imidazole: { label: "Imidazole (C₃H₄N₂)", atoms: [["C",-1.014,0.697,-0.096],["C",-0.759,-0.653,-0.071],["N",0.599,-0.755,0.057],["C",1.102,0.514,0.104],["N",0.150,1.413,0.014],["H",-1.973,1.192,-0.186],["H",-1.402,-1.519,-0.132],["H",1.138,-1.608,0.108],["H",2.160,0.718,0.204]] },
  thiophene: { label: "Thiophene (C₄H₄S)", atoms: [["C",0.698,-0.723,0.012],["C",-0.715,-0.686,-0.170],["C",-1.212,0.596,-0.094],["S",0.021,1.748,0.196],["C",1.225,0.532,0.220],["H",1.298,-1.625,-0.009],["H",-1.336,-1.556,-0.348],["H",-2.240,0.916,-0.194],["H",2.260,0.798,0.386]] },
  formamide: { label: "Formamide (CH₃NO)", atoms: [["C",0.644,0.120,-0.119],["O",1.512,-0.722,0.055],["N",-0.674,-0.109,0.119],["H",0.847,1.139,-0.484],["H",-1.384,0.594,-0.028],["H",-0.946,-1.023,0.457]] },
  urea: { label: "Urea (CH₄N₂O)", atoms: [["N",-1.109,-0.321,0.075],["C",-0.022,0.478,0.009],["O",-0.079,1.695,0.033],["N",1.134,-0.213,-0.085],["H",-0.993,-1.167,0.614],["H",-1.959,0.190,0.281],["H",1.932,0.382,-0.270],["H",1.096,-1.045,-0.657]] },
  glycine: { label: "Glycine (C₂H₅NO₂)", atoms: [["N",-1.399,0.591,0.239],["C",-0.631,-0.480,-0.429],["C",0.862,-0.396,-0.133],["O",1.700,-1.230,-0.439],["O",1.234,0.735,0.506],["H",-1.244,0.509,1.245],["H",-0.953,1.480,-0.002],["H",-0.773,-0.399,-1.510],["H",-1.001,-1.448,-0.080],["H",2.205,0.637,0.604]] },
  uracil: { label: "Uracil (C₄H₄N₂O₂)", atoms: [["O",2.582,-0.513,0.003],["C",1.378,-0.280,0.002],["C",0.874,1.108,-0.006],["C",-0.446,1.311,-0.008],["N",-1.316,0.258,-0.002],["C",-0.921,-1.054,0.006],["O",-1.730,-1.975,0.011],["N",0.429,-1.263,0.007],["H",1.602,1.908,-0.011],["H",-0.880,2.305,-0.013],["H",-2.318,0.414,-0.003],["H",0.747,-2.219,0.013]] },
  thymine: { label: "Thymine (C₅H₆N₂O₂)", atoms: [["C",-2.213,-0.190,0.151],["C",-0.725,-0.124,0.057],["C",0.089,-1.184,0.136],["N",1.446,-1.048,0.042],["C",2.077,0.152,-0.138],["O",3.298,0.238,-0.219],["N",1.259,1.241,-0.221],["C",-0.106,1.215,-0.139],["O",-0.783,2.234,-0.222],["H",-2.572,0.404,0.997],["H",-2.565,-1.218,0.294],["H",-2.673,0.194,-0.766],["H",-0.281,-2.194,0.279],["H",2.052,-1.858,0.104],["H",1.698,2.138,-0.354]] },
  cytosine: { label: "Cytosine (C₄H₅N₃O)", atoms: [["N",2.291,-0.133,-0.279],["C",0.932,-0.007,-0.190],["C",0.156,-0.997,0.595],["C",-1.160,-0.795,0.634],["N",-1.703,0.268,-0.021],["C",-0.966,1.174,-0.747],["O",-1.547,2.101,-1.304],["N",0.394,1.000,-0.808],["H",2.720,0.710,-0.651],["H",2.770,-0.490,0.538],["H",0.654,-1.823,1.079],["H",-1.841,-1.449,1.167],["H",-2.699,0.442,-0.012]] },
  adenine: { label: "Adenine (C₅H₅N₅)", atoms: [["N",-2.061,-1.393,-0.699],["C",-1.266,-0.336,-0.275],["N",-1.875,0.818,0.088],["C",-1.102,1.850,0.496],["N",0.241,1.898,0.614],["C",0.785,0.726,0.258],["N",2.110,0.401,0.256],["C",2.216,-0.897,-0.166],["N",1.039,-1.424,-0.436],["C",0.133,-0.412,-0.183],["H",-3.012,-1.314,-0.364],["H",-1.605,-2.295,-0.622],["H",-1.635,2.758,0.764],["H",2.862,1.018,0.523],["H",3.170,-1.400,-0.255]] },
  azobenzene: { label: "Azobenzene (C₁₂H₁₀N₂)", atoms: [["C",-4.447,0.576,-0.037],["C",-3.834,-0.592,-0.489],["C",-2.462,-0.775,-0.305],["C",-1.688,0.210,0.324],["C",-2.319,1.371,0.784],["C",-3.691,1.557,0.601],["N",-0.310,0.041,0.552],["N",0.305,-0.082,-0.530],["C",1.685,-0.239,-0.303],["C",2.198,-1.329,0.413],["C",3.575,-1.476,0.596],["C",4.452,-0.537,0.056],["C",3.955,0.545,-0.669],["C",2.577,0.689,-0.850],["H",-5.515,0.719,-0.180],["H",-4.422,-1.361,-0.984],["H",-1.988,-1.689,-0.653],["H",-1.732,2.136,1.286],["H",-4.168,2.466,0.959],["H",1.517,-2.067,0.830],["H",3.960,-2.323,1.158],["H",5.524,-0.650,0.198],["H",4.637,1.276,-1.094],["H",2.192,1.531,-1.419]] },
  stilbene: { label: "trans-Stilbene (C₁₄H₁₂)", atoms: [["C",-4.650,-0.513,-0.180],["C",-4.028,0.373,0.697],["C",-2.636,0.378,0.817],["C",-1.851,-0.496,0.053],["C",-2.490,-1.393,-0.813],["C",-3.882,-1.398,-0.933],["C",-0.387,-0.544,0.172],["C",0.387,0.544,0.318],["C",1.851,0.496,0.437],["C",2.636,-0.378,-0.327],["C",4.028,-0.373,-0.206],["C",4.650,0.513,0.670],["C",3.882,1.398,1.424],["C",2.490,1.393,1.303],["H",-5.733,-0.518,-0.273],["H",-4.626,1.057,1.293],["H",-2.174,1.064,1.522],["H",-1.907,-2.092,-1.409],["H",-4.365,-2.094,-1.614],["H",0.052,-1.538,0.127],["H",-0.052,1.538,0.363],["H",2.174,-1.064,-1.032],["H",4.626,-1.057,-0.803],["H",5.733,0.518,0.763],["H",4.365,2.094,2.105],["H",1.907,2.092,1.899]] },
  retinalPSB: { label: "PSB3 model (C₅H₈N⁺)", atoms: [["C",-0.579,0.222,0.149],["C",0.631,-0.354,0.187],["C",1.784,0.474,0.566],["N",2.978,0.016,0.631],["C",-1.773,-0.507,-0.211],["C",-2.984,0.061,-0.251],["H",-0.714,1.276,0.391],["H",0.767,-1.404,-0.054],["H",1.623,1.538,0.806],["H",3.763,0.614,0.897],["H",3.202,-0.957,0.422],["H",-1.688,-1.563,-0.461],["H",-3.153,1.108,-0.016],["H",-3.858,-0.524,-0.527]] },
  caffeine: { label: "Caffeine (C₈H₁₀N₄O₂)", atoms: [["C",3.294,0.253,0.440],["N",2.076,-0.507,0.312],["C",1.964,-1.871,0.367],["N",0.714,-2.262,0.215],["C",0.013,-1.105,0.059],["C",0.820,-0.009,0.113],["C",0.338,1.321,-0.022],["O",1.075,2.301,0.029],["N",-1.045,1.378,-0.215],["C",-1.660,2.682,-0.367],["C",-1.914,0.268,-0.277],["O",-3.126,0.421,-0.452],["N",-1.343,-0.997,-0.133],["C",-2.167,-2.191,-0.185],["H",3.200,0.918,1.302],["H",3.445,0.826,-0.478],["H",4.135,-0.429,0.591],["H",2.813,-2.526,0.518],["H",-2.167,2.725,-1.337],["H",-2.409,2.816,0.420],["H",-0.936,3.498,-0.310],["H",-1.826,-2.825,-1.009],["H",-2.070,-2.733,0.761],["H",-3.222,-1.951,-0.342]] },
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
  if (name === "analysis") refreshJobs();
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
    xyzArea.value = atomsToText(SAMPLES[key].atoms);
    updatePreview();
  }
});

// --- open an existing file: OpenQP inputs/outputs, trajectories, and the
// common interchange formats. Multi-geometry files become a frame slider. ---
let loadedFrames: { label: string; atoms: Atom[] }[] = [];

function showFrame(index: number): void {
  const frame = loadedFrames[index - 1];
  if (!frame) return;
  xyzArea.value = atomsToText(frame.atoms);
  $<HTMLSpanElement>("frameLabel").textContent =
    loadedFrames.length > 1
      ? `${index} / ${loadedFrames.length}  ${frame.label}`
      : frame.label;
  updatePreview();
}

$<HTMLInputElement>("frameRange").addEventListener("input", (event) => {
  showFrame(+(event.target as HTMLInputElement).value);
});

$<HTMLInputElement>("fileInput").addEventListener("change", async (event) => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  showBusy("Reading structure", file.name);
  try {
    const body = new FormData();
    body.append("file", file);
    const res = await fetch("/api/structure/open", { method: "POST", body });
    if (!res.ok) {
      builderStatus.textContent = `${file.name}: ${(await res.json()).detail ?? res.status}`;
      return;
    }
    const data = await res.json();
    if (/\.(pdb|ent|cif)$/i.test(file.name)) {
      // Mol* reads PDB natively; going through plain coordinates would throw
      // away the residues and chains a cartoon needs.
      const text = await file.text();
      $<HTMLIFrameElement>("previewFrame").src ||= "/builder3d.html";
      setTimeout(
        () => $<HTMLIFrameElement>("previewFrame").contentWindow?.postMessage(
          { type: "oqp-file", text, format: "pdb" }, window.location.origin),
        viewerReady ? 0 : 800,
      );
    }
    loadedFrames = data.frames;
    const slider = $<HTMLInputElement>("frameRange");
    slider.max = String(loadedFrames.length);
    slider.value = String(loadedFrames.length);   // land on the final geometry
    $<HTMLDivElement>("frameRow").style.display =
      loadedFrames.length > 1 ? "flex" : "none";
    showFrame(loadedFrames.length);
    builderStatus.textContent =
      `${data.format} · ${loadedFrames[0].atoms.length} atoms` +
      (loadedFrames.length > 1 ? ` · ${loadedFrames.length} frames` : "");
  } finally {
    hideBusy();
  }
});

// Proteins and nucleic acids come from the RCSB Protein Data Bank, not from
// PubChem; the file is handed to the viewer whole so chains and residues
// survive for the cartoon representation.
$<HTMLButtonElement>("pdbFetch").addEventListener("click", async () => {
  const code = $<HTMLInputElement>("pdbCode").value.trim();
  if (!code) return;
  showBusy("Fetching from the PDB", `entry ${code.toUpperCase()}…`);
  try {
    const response = await fetch(`/api/pdb/${encodeURIComponent(code)}`);
    if (!response.ok) throw new Error((await response.json()).detail ?? response.statusText);
    const data = await response.json();
    const frame = document.getElementById("previewFrame") as HTMLIFrameElement;
    frame.src ||= "/builder3d.html";
    const send = () => frame.contentWindow?.postMessage(
      { type: "oqp-file", text: data.pdb, format: "pdb" }, window.location.origin);
    setTimeout(send, viewerReady ? 0 : 800);

    // The coordinate box gets the same structure, so it can be run as input.
    const body = new FormData();
    body.append("file", new File([data.pdb], `${data.code}.pdb`));
    const parsed = await fetch("/api/structure/open", { method: "POST", body });
    if (parsed.ok) {
      const structure = await parsed.json();
      loadedFrames = structure.frames;
      xyzArea.value = atomsToText(loadedFrames[0].atoms);
      builderStatus.textContent =
        `${data.code} · ${loadedFrames[0].atoms.length} atoms from the PDB`;
    }
  } catch (err) {
    const message = (err as Error).message;
    builderStatus.textContent = `PDB: ${message}`;
    if (/certificate/i.test(message)) {
      hideBusy();
      await openNetworkSettings();
    }
  } finally {
    hideBusy();
  }
});

$<HTMLButtonElement>("pubchemFetch").addEventListener("click", async () => {
  const name = $<HTMLInputElement>("pubchemName").value.trim();
  if (!name) return;
  showBusy("Fetching from PubChem", `looking up “${name}”…`);
  try {
    const res = await fetch(`/api/pubchem/${encodeURIComponent(name)}`);
    if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
    const data = await res.json();
    xyzArea.value = atomsToText(data.atoms);
    builderStatus.textContent = `${data.atoms.length} atoms loaded from PubChem`;
    await updatePreview();
  } catch (err) {
    const message = (err as Error).message;
    builderStatus.textContent = `PubChem: ${message}`;
    // A certificate failure has a fix, so take the user straight to it.
    if (/certificate/i.test(message)) {
      hideBusy();
      await openNetworkSettings();
    }
  } finally {
    hideBusy();
  }
});

// A spinner for the steps that take a noticeable moment: the first
// sketch-to-3D conversion loads RDKit, and PubChem is a network round trip.
const busy = $<HTMLDivElement>("busy");
let busyTimer: number | undefined;

function showBusy(message: string, sub = ""): void {
  $<HTMLDivElement>("busyMsg").textContent = message;
  const subEl = $<HTMLDivElement>("busySub");
  subEl.textContent = sub;
  busy.classList.add("on");
  const started = Date.now();
  clearInterval(busyTimer);
  busyTimer = window.setInterval(() => {
    const seconds = Math.round((Date.now() - started) / 1000);
    subEl.textContent = seconds >= 3 ? `${sub} ${seconds}s` : sub;
  }, 1000);
}

function hideBusy(): void {
  clearInterval(busyTimer);
  busy.classList.remove("on");
}

// --- 2D sketcher (Ketcher in a modal; RDKit turns the sketch into 3D) ---
const sketchOverlay = $<HTMLDivElement>("sketchOverlay");
$<HTMLButtonElement>("sketchBtn").addEventListener("click", () => {
  const frame = $<HTMLIFrameElement>("sketchFrame");
  if (!frame.src) frame.src = "/sketcher.html";
  sketchOverlay.style.display = "";
});
$<HTMLButtonElement>("sketchClose").addEventListener("click", () => {
  sketchOverlay.style.display = "none";
});
window.addEventListener("message", async (event) => {
  if (event.origin !== window.location.origin) return;
  if (event.data?.type !== "oqp-sketch") return;
  sketchOverlay.style.display = "none";
  showBusy("Building 3D structure", "embedding and optimizing with RDKit…");
  try {
    const res = await fetch("/api/structure3d", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ molfile: event.data.molfile }),
    });
    if (!res.ok) {
      builderStatus.textContent = `3D build failed: ${(await res.json()).detail ?? res.status}`;
      return;
    }
    const data = await res.json();
    xyzArea.value = atomsToText(data.atoms);
    builderStatus.textContent = `${data.atoms.length} atoms from sketch (RDKit ETKDG + MMFF)`;
    await updatePreview();
  } finally {
    hideBusy();
  }
});

// Display options are shared by both viewers so a molecule looks the same
// wherever it is shown. "auto" keeps Mol*'s own preset, which is what the app
// has always drawn — and what turns a PDB into a protein cartoon.
const displayStyle: Record<string, string> = {
  type: "auto",
  color: "element-symbol",
  labels: "none",
};

function pushStyle(): void {
  const message = { type: "oqp-style", style: displayStyle };
  for (const id of ["previewFrame", "resultFrame"]) {
    const frame = document.getElementById(id) as HTMLIFrameElement | null;
    if (frame?.src) frame.contentWindow?.postMessage(message, window.location.origin);
  }
}

const rendering: Record<string, boolean | number> = {
  occlusion: true,
  outline: true,
  background: 0x1b1e24,
};

function pushToViewers(message: Record<string, unknown>): void {
  for (const id of ["previewFrame", "resultFrame"]) {
    const frame = document.getElementById(id) as HTMLIFrameElement | null;
    if (frame?.src) frame.contentWindow?.postMessage(message, window.location.origin);
  }
}

document.querySelectorAll<HTMLInputElement | HTMLSelectElement>(".render-input").forEach((input) => {
  input.addEventListener("change", () => {
    const key = input.dataset.render!;
    rendering[key] = input instanceof HTMLInputElement && input.type === "checkbox"
      ? input.checked
      : parseInt(input.value, 16);
    document.querySelectorAll<HTMLInputElement | HTMLSelectElement>(
      `.render-input[data-render="${key}"]`,
    ).forEach((twin) => {
      if (twin instanceof HTMLInputElement && twin.type === "checkbox") {
        twin.checked = input instanceof HTMLInputElement && input.checked;
      } else {
        twin.value = input.value;
      }
    });
    pushToViewers({ type: "oqp-rendering", rendering });
  });
});

// Orbital phase colours, opacity and surface kind, as MacMolPlt and IQmol offer.
function pushOrbitalStyle(): void {
  const [positive, negative] = $<HTMLSelectElement>("moColors").value.split(",");
  pushToViewers({
    type: "oqp-orbital-style",
    orbital: {
      positive: parseInt(positive, 16),
      negative: parseInt(negative, 16),
      alpha: +$<HTMLInputElement>("moAlpha").value,
      visuals: $<HTMLSelectElement>("moVisual").value.split(","),
    },
  });
}

// Ready-made orbital looks. "studio" is what the app has always drawn and
// stays the default; the MacMolPlt entries reproduce that program's opaque
// red/blue lobes, solid or as a mesh.
const MO_PRESETS: Record<string, { colors: string; visual: string; alpha: string }> = {
  studio: { colors: "4f8fdd,dd6a4f", visual: "solid", alpha: "0.85" },
  macmolplt: { colors: "d64a3b,3b6fd6", visual: "solid", alpha: "1" },
  "macmolplt-mesh": { colors: "d64a3b,3b6fd6", visual: "wireframe", alpha: "1" },
  iqmol: { colors: "3b6fd6,e0b93a", visual: "solid", alpha: "0.55" },
  print: { colors: "d9dde4,7b8494", visual: "solid,wireframe", alpha: "1" },
};

const moPreset = $<HTMLSelectElement>("moPreset");
const moColors = $<HTMLSelectElement>("moColors");
const moVisual = $<HTMLSelectElement>("moVisual");
const moAlpha = $<HTMLInputElement>("moAlpha");

moPreset.addEventListener("change", () => {
  const preset = MO_PRESETS[moPreset.value];
  if (!preset) return;                       // "custom" leaves the controls alone
  moColors.value = preset.colors;
  moVisual.value = preset.visual;
  moAlpha.value = preset.alpha;
  showOrbital();                             // colours are baked into the volume
});

for (const id of ["moColors", "moVisual", "moAlpha"]) {
  $<HTMLElement>(id).addEventListener("change", () => {
    moPreset.value = "custom";
    // Colours are baked in when the volume loads, so redraw for those.
    if (id === "moColors") showOrbital();
    else pushOrbitalStyle();
  });
}

document.querySelectorAll<HTMLSelectElement>(".style-input").forEach((select) => {
  select.addEventListener("change", () => {
    displayStyle[select.dataset.style!] = select.value;
    // Keep the duplicate control in the other tab in step.
    document.querySelectorAll<HTMLSelectElement>(
      `.style-input[data-style="${select.dataset.style}"]`,
    ).forEach((twin) => { twin.value = select.value; });
    pushStyle();
  });
});

// The preview iframe hosts one long-lived Mol* viewer; structures are pushed
// into it rather than reloading the page, which would re-initialize WebGL.
let viewerReady = false;
window.addEventListener("message", (event) => {
  if (event.origin === window.location.origin && event.data?.type === "oqp-viewer-ready") {
    viewerReady = true;
    updatePreview();
  }
});

async function updatePreview(): Promise<void> {
  const atoms = parseAtoms(xyzArea.value);
  if (!atoms.length) return;
  const xyz = `${atoms.length}\nOQP Studio preview\n${atomsToText(atoms)}\n`;
  const frame = $<HTMLIFrameElement>("previewFrame");
  if (!frame.src) {
    frame.src = "/builder3d.html";   // pushes arrive once it reports ready
    return;
  }
  if (!viewerReady) return;
  frame.contentWindow?.postMessage(
    { type: "oqp-structure", xyz },
    window.location.origin,
  );
}
$<HTMLButtonElement>("previewBtn").addEventListener("click", updatePreview);

function buildSampleList(): void {
  const select = $<HTMLSelectElement>("sample");
  for (const [key, sample] of Object.entries(SAMPLES)) {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = sample.label;
    select.appendChild(option);
  }
}

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
  const info = $<HTMLSpanElement>("runnersInfo");
  info.textContent =
    "runners: " + Object.entries(runners).map(([n, ok]) => `${n} ${ok ? "✓" : "✗"}`).join(" · ");
  // Say which openqp was found: "local ✓" is not much use without the path,
  // and "local ✗" needs to say where the app looked.
  try {
    const detail = await (await fetch("/api/runners/detail")).json();
    info.title = detail.openqp
      ? `native openqp: ${detail.openqp}`
      : `no openqp on PATH — searched:\n${(detail.path_entries ?? []).join("\n")}`;
    if (detail.openqp) info.textContent += `  (${detail.openqp})`;
  } catch {
    // The footer is decoration; a missing detail endpoint is not worth a fuss.
  }
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
  loadSummary(jobId).catch(() => {});
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

// Energies, states, frequencies and properties, read back from whatever the
// job wrote — the JSON export when there is one, the log otherwise.
async function loadSummary(jobId: string): Promise<void> {
  $<HTMLDivElement>("summaryCard").style.display = "none";
  $<HTMLDivElement>("spectrumCard").style.display = "none";
  const response = await fetch(`/api/jobs/${jobId}/summary?refresh=true`);
  if (!response.ok) return;
  summary = await response.json();
  renderSummary(summary!);
  buildSpectrumList(summary!);
  if ($<HTMLDivElement>("spectrumCard").style.display === "") await loadSpectrum();
}

const resultFrame = $<HTMLIFrameElement>("resultFrame");
const orbitalCard = $<HTMLDivElement>("orbitalCard");
const orbitalSel = $<HTMLSelectElement>("orbitalSel");
const isoRange = $<HTMLInputElement>("isoRange");
const modeCard = $<HTMLDivElement>("modeCard");
const modeSel = $<HTMLSelectElement>("modeSel");
const amplitudeRange = $<HTMLInputElement>("ampRange");
let currentMolden: { jobId: string; name: string } | null = null;
let resultFrames: { label: string; atoms: Atom[] }[] = [];
let resultViewerReady = false;

// Everything in Analysis renders through the same Mol* page the Builder uses,
// so results look like the rest of the app rather than a second program.
window.addEventListener("message", (event) => {
  if (event.origin === window.location.origin && event.data?.type === "oqp-viewer-ready") {
    resultViewerReady = true;
  }
});

function pushToResultViewer(message: Record<string, unknown>): void {
  const send = () => resultFrame.contentWindow?.postMessage(message, window.location.origin);
  if (!resultFrame.src) {
    resultFrame.src = "/builder3d.html";
    resultFrame.addEventListener("load", () => setTimeout(send, 400), { once: true });
    return;
  }
  if (resultViewerReady) send();
  else setTimeout(send, 600);
}

function showResultFrame(index: number): void {
  const frame = resultFrames[index - 1];
  if (!frame) return;
  const xyz = `${frame.atoms.length}\n${frame.label}\n${atomsToText(frame.atoms)}\n`;
  $<HTMLSpanElement>("resultFrameLabel").textContent =
    resultFrames.length > 1 ? `${index} / ${resultFrames.length}  ${frame.label}` : frame.label;
  pushToResultViewer({ type: "oqp-structure", xyz });
}

$<HTMLInputElement>("resultFrameRange").addEventListener("input", (event) => {
  showResultFrame(+(event.target as HTMLInputElement).value);
});

function hideResultPanels(): void {
  orbitalCard.style.display = "none";
  $<HTMLDivElement>("levelCard").style.display = "none";
  modeCard.style.display = "none";
  $<HTMLDivElement>("resultFrameCard").style.display = "none";
  currentMolden = null;
}

async function viewResultFile(jobId: string, name: string, url: string): Promise<void> {
  const lower = name.toLowerCase();
  hideResultPanels();

  if (lower.endsWith(".cube") || lower.endsWith(".cub")) {
    pushToResultViewer({ type: "oqp-cube", cube: url, iso: 0.05 });
    return;
  }

  if (lower.endsWith(".molden")) {
    const base = `/api/jobs/${jobId}/molden/${encodeURIComponent(name)}`;
    currentMolden = { jobId, name };
    const [orbitals, modes] = await Promise.all([
      fetch(`${base}/orbitals`).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch(`${base}/modes`).then((r) => (r.ok ? r.json() : null)).catch(() => null),
    ]);
    if (orbitals?.orbitals?.length) {
      orbitalSel.innerHTML = "";
      for (const o of orbitals.orbitals) {
        const opt = document.createElement("option");
        opt.value = String(o.index);
        const occ = o.occupancy != null ? ` occ=${o.occupancy}` : "";
        opt.textContent = `MO ${o.index}  E=${o.energy.toFixed(4)} Ha${occ} ${o.spin}`;
        orbitalSel.appendChild(opt);
      }
      const homo = [...orbitals.orbitals].reverse()
        .find((o: { occupancy: number | null }) => (o.occupancy ?? 0) > 1e-6);
      if (homo) orbitalSel.value = String(homo.index);
      orbitalCard.style.display = "";
      drawLevels(orbitals.orbitals);
      showOrbital();
    }
    if (modes?.modes?.length) {
      modeSel.innerHTML = "";
      for (const m of modes.modes) {
        const opt = document.createElement("option");
        opt.value = String(m.index);
        const ir = m.intensity != null ? `  IR ${m.intensity.toFixed(2)}` : "";
        opt.textContent = `Mode ${m.index}  ${m.frequency.toFixed(1)} cm⁻¹${ir}`;
        modeSel.appendChild(opt);
      }
      modeCard.style.display = "";
      if (!orbitals?.orbitals?.length) showMode();
    }
    if (!orbitals?.orbitals?.length && !modes?.modes?.length) {
      await openAsStructure(name, url);
    }
    return;
  }

  await openAsStructure(name, url);
}

// Reads the file through the same importer the Builder uses, so OpenQP logs,
// JSON, inputs and trajectories all render as geometry here.
async function openAsStructure(name: string, url: string): Promise<void> {
  try {
    const blob = await (await fetch(url)).blob();
    const body = new FormData();
    body.append("file", new File([blob], name));
    const res = await fetch("/api/structure/open", { method: "POST", body });
    if (!res.ok) return;
    const data = await res.json();
    resultFrames = data.frames;
    const slider = $<HTMLInputElement>("resultFrameRange");
    slider.max = String(resultFrames.length);
    slider.value = String(resultFrames.length);
    $<HTMLDivElement>("resultFrameCard").style.display =
      resultFrames.length > 1 ? "" : "none";
    showResultFrame(resultFrames.length);
  } catch {
    // Nothing renderable in this file; the download link still works.
  }
}

// Isovalues that suit each field: orbitals peak near 0.05, the density is
// conventionally drawn at 0.002, and the MEP is a potential in Hartree/e.
const MAP_ISO: Record<string, number> = {
  mo: 0.05, density: 0.002, spin: 0.004, esp: 0.03,
};

const mapKind = $<HTMLSelectElement>("mapKind");

function mapUrl(base: string): string {
  return mapKind.value === "mo"
    ? `${base}/cube?mo=${orbitalSel.value}`
    : `${base}/map?kind=${mapKind.value}`;
}

function showOrbital(): void {
  if (!currentMolden) return;
  pushOrbitalStyle();
  $<HTMLDivElement>("orbitalPick").style.display = mapKind.value === "mo" ? "" : "none";
  const base = `/api/jobs/${currentMolden.jobId}/molden/${encodeURIComponent(currentMolden.name)}`;
  const iso = +isoRange.value;
  fetch(`${base}/geom.xyz`)
    .then((r) => r.text())
    .then((xyz) =>
      pushToResultViewer({
        type: "oqp-cube",
        xyz,
        cube: mapUrl(base),
        iso,
      }),
    );
}
orbitalSel.addEventListener("change", showOrbital);
isoRange.addEventListener("change", showOrbital);
mapKind.addEventListener("change", () => {
  // Each field has its own natural contour, so move the slider with it.
  isoRange.value = String(MAP_ISO[mapKind.value] ?? 0.05);
  showOrbital();
});

function showMode(): void {
  if (!currentMolden) return;
  const base = `/api/jobs/${currentMolden.jobId}/molden/${encodeURIComponent(currentMolden.name)}`;
  fetch(`${base}/mode.xyz?mode=${modeSel.value}&amplitude=${amplitudeRange.value}`)
    .then((r) => r.text())
    .then((xyz) => pushToResultViewer({ type: "oqp-structure", xyz }));
}
modeSel.addEventListener("change", showMode);
amplitudeRange.addEventListener("change", showMode);

// ---------- results summary ----------
type Summary = {
  energy: { total?: number; components?: Record<string, number>;
            final_states?: Record<string, number> };
  scf: { method?: string; energy?: number; iterations?: number; converged?: boolean };
  states: { index: number; total: number; excitation_ev: number;
            excitation_nm: number | null; oscillator: number | null }[];
  frequencies: { index: number; frequency: number; ir: number | null; raman: number | null }[];
  thermochemistry: Record<string, number>;
  charges: Record<string, number[]>;
  dipole: { x: number; y: number; z: number; total_au: number; total_debye: number } | null;
  symmetry: { point_group: string; detected: string | null; enabled: boolean } | null;
  units: { ir: string; raman: string };
  has_frequencies: boolean;
  has_states: boolean;
  has_oscillators: boolean;
};

let summary: Summary | null = null;

const ENERGY_LABELS: Record<string, string> = {
  total: "Total energy",
  one_electron: "One-electron energy",
  two_electron: "Two-electron energy",
  nuclear_repulsion: "Nuclear repulsion",
  potential: "Potential energy",
  kinetic: "Kinetic energy",
  virial_ratio: "Virial ratio (V/T)",
};

const THERMO_LABELS: Record<string, string> = {
  temperature: "Temperature (K)",
  pressure: "Pressure (atm)",
  zpe: "Zero-point energy",
  internal_energy: "Internal energy U",
  enthalpy: "Enthalpy H",
  gibbs_free_energy: "Gibbs free energy G",
};

function rows(pairs: [string, string][]): string {
  return pairs.length
    ? `<table class="sum">${pairs
        .map(([k, v]) => `<tr><td class="k">${k}</td><td class="v">${v}</td></tr>`)
        .join("")}</table>`
    : "";
}

function fixed(value: number, digits = 6): string {
  return Number.isFinite(value) ? value.toFixed(digits) : "—";
}

function renderSummary(data: Summary): void {
  const parts: string[] = [];

  const energy: [string, string][] = [];
  if (data.scf.energy !== undefined) {
    energy.push([`${data.scf.method ?? "SCF"} energy (Ha)`, fixed(data.scf.energy, 8)]);
  }
  if (data.scf.iterations !== undefined) {
    energy.push(["SCF iterations", String(data.scf.iterations)]);
  }
  if (data.scf.converged !== undefined) {
    energy.push(["Converged", data.scf.converged ? "yes" : "no"]);
  }
  for (const [key, label] of Object.entries(ENERGY_LABELS)) {
    const value = data.energy.components?.[key];
    if (value === undefined) continue;
    // The virial ratio is dimensionless; everything else here is in Hartree.
    energy.push([key === "virial_ratio" ? label : `${label} (Ha)`, fixed(value)]);
  }
  if (energy.length) parts.push(`<div class="sum-title">Energy</div>${rows(energy)}`);

  if (data.symmetry?.point_group) {
    const upper = (text: string) =>
      text.charAt(0).toUpperCase() + text.slice(1);
    parts.push('<div class="sum-title">Symmetry</div>' + rows([
      ["Point group", upper(data.symmetry.point_group)],
      ["Detected", upper(data.symmetry.detected ?? data.symmetry.point_group)],
      ["Used in the run", data.symmetry.enabled ? "yes" : "no"],
    ]));
  }

  if (data.dipole) {
    parts.push('<div class="sum-title">Dipole moment</div>' + rows([
      ["x, y, z (a.u.)",
       `${fixed(data.dipole.x, 4)}, ${fixed(data.dipole.y, 4)}, ${fixed(data.dipole.z, 4)}`],
      ["Magnitude (Debye)", fixed(data.dipole.total_debye, 4)],
    ]));
  }

  if (data.states.length > 1) {
    const head = "<tr><th>State</th><th>ΔE (eV)</th><th>λ (nm)</th><th>f</th></tr>";
    const body = data.states.slice(1).map((state) =>
      `<tr><td class="k">S${state.index}</td>` +
      `<td class="v">${state.excitation_ev.toFixed(3)}</td>` +
      `<td class="v">${state.excitation_nm ? state.excitation_nm.toFixed(1) : "—"}</td>` +
      `<td class="v">${state.oscillator != null ? state.oscillator.toFixed(4) : "—"}</td></tr>`,
    ).join("");
    parts.push(`<div class="sum-title">Excited states</div>` +
      `<table class="sum">${head}${body}</table>` +
      (data.has_oscillators ? "" :
        '<div class="hint">the output carries no oscillator strengths</div>'));
  }

  if (data.frequencies.length) {
    const head = `<tr><th>Mode</th><th>cm⁻¹</th><th>IR (${data.units.ir})</th>` +
      `<th>Raman (${data.units.raman})</th></tr>`;
    const body = data.frequencies.map((mode) =>
      `<tr><td class="k">${mode.index}</td><td class="v">${mode.frequency.toFixed(1)}</td>` +
      `<td class="v">${mode.ir != null ? mode.ir.toFixed(3) : "—"}</td>` +
      `<td class="v">${mode.raman != null ? mode.raman.toFixed(2) : "—"}</td></tr>`,
    ).join("");
    const imaginary = data.frequencies.filter((m) => m.frequency < 0).length;
    parts.push(`<div class="sum-title">Vibrations</div>` +
      `<table class="sum">${head}${body}</table>` +
      (imaginary
        ? `<div class="hint">${imaginary} imaginary mode(s): this is a saddle point</div>`
        : ""));
  }

  const thermo = Object.entries(THERMO_LABELS)
    .filter(([key]) => data.thermochemistry[key] !== undefined)
    .map(([key, label]) => [label, fixed(data.thermochemistry[key])] as [string, string]);
  if (thermo.length) {
    parts.push(`<div class="sum-title">Thermochemistry</div>${rows(thermo)}`);
  }

  const charge = Object.entries(data.charges)[0];
  if (charge) {
    const [source, values] = charge;
    parts.push(`<div class="sum-title">Partial charges (${source})</div>` +
      rows(values.map((q, i) => [`Atom ${i + 1}`, fixed(q, 4)] as [string, string])));
  }

  const body = $<HTMLDivElement>("summaryBody");
  body.innerHTML = parts.length
    ? parts.join("")
    : '<div class="hint">nothing summarisable in this job\u2019s output yet</div>';
  $<HTMLDivElement>("summaryCard").style.display = parts.length ? "" : "none";
}

// ---------- spectra ----------
const SPECTRA: { value: string; label: string; needs: "freq" | "states" }[] = [
  { value: "ir", label: "IR absorption", needs: "freq" },
  { value: "raman", label: "Raman", needs: "freq" },
  { value: "absorption", label: "UV/Vis absorption", needs: "states" },
  { value: "emission", label: "Emission (Kasha)", needs: "states" },
  { value: "esa", label: "Excited-state absorption", needs: "states" },
];

const specKind = $<HTMLSelectElement>("specKind");
const specShape = $<HTMLSelectElement>("specShape");
const specWidth = $<HTMLInputElement>("specWidth");
const specState = $<HTMLInputElement>("specState");

function buildSpectrumList(data: Summary): void {
  const usable = SPECTRA.filter((entry) =>
    entry.needs === "freq" ? data.has_frequencies : data.has_states);
  specKind.innerHTML = "";
  for (const entry of usable) {
    const option = document.createElement("option");
    option.value = entry.value;
    option.textContent = entry.label;
    specKind.appendChild(option);
  }
  $<HTMLDivElement>("spectrumCard").style.display = usable.length ? "" : "none";
  if (usable.length) syncSpectrumControls();
}

// Vibrational widths are in cm-1, electronic ones in eV, so the slider has to
// change meaning with the spectrum.
function vibrationalKind(): boolean {
  return specKind.value === "ir" || specKind.value === "raman";
}

function syncSpectrumControls(): void {
  const vibrational = vibrationalKind();
  specWidth.min = vibrational ? "1" : "1";
  specWidth.max = vibrational ? "100" : "100";
  const width = widthValue();
  $<HTMLSpanElement>("specWidthLabel").textContent =
    vibrational ? `${width.toFixed(0)} cm⁻¹` : `${width.toFixed(2)} eV`;
  $<HTMLDivElement>("specStateWrap").style.display =
    specKind.value === "emission" || specKind.value === "esa" ? "" : "none";
}

function widthValue(): number {
  const raw = +specWidth.value;
  return vibrationalKind() ? raw : raw / 100;   // slider steps of 0.01 eV
}

async function loadSpectrum(): Promise<void> {
  if (!selectedJob) return;
  syncSpectrumControls();
  const query = new URLSearchParams({
    kind: specKind.value,
    shape: specShape.value,
    fwhm: String(widthValue()),
    state: specState.value,
  });
  const data = await (await fetch(`/api/jobs/${selectedJob}/spectrum?${query}`)).json();
  drawSpectrum(data);
}

type SpectrumData = {
  available: boolean; reason?: string;
  x: number[]; y: number[]; x_nm?: number[];
  sticks: { position: number; intensity: number; position_nm?: number }[];
  x_label: string; y_label: string; reverse_x: boolean;
  estimated_intensities?: boolean; title?: string;
};

function drawSpectrum(data: SpectrumData): void {
  lastSpectrum = data;
  const plot = $<HTMLDivElement>("specPlot");
  const note = $<HTMLDivElement>("specNote");
  if (!data.available || !data.x.length) {
    plot.innerHTML = "";
    note.textContent = data.reason ?? "no spectrum for this job";
    return;
  }

  const w = 520, h = 240, pad = { l: 52, r: 12, t: 10, b: 34 };
  const xs = data.x, ys = data.y;
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMax = Math.max(...ys, 1e-12);
  const flip = data.reverse_x;
  const sx = (x: number) => {
    const t = (x - xMin) / (xMax - xMin || 1);
    return pad.l + (flip ? 1 - t : t) * (w - pad.l - pad.r);
  };
  const sy = (y: number) => h - pad.b - (y / yMax) * (h - pad.t - pad.b);

  const path = xs.map((x, i) => `${i ? "L" : "M"}${sx(x).toFixed(1)},${sy(ys[i]).toFixed(1)}`)
    .join("");
  const stickMax = Math.max(...data.sticks.map((s) => s.intensity), 1e-12);
  const sticks = data.sticks.map((stick) => {
    const x = sx(stick.position).toFixed(1);
    const top = sy((stick.intensity / stickMax) * yMax * 0.92).toFixed(1);
    return `<line x1="${x}" y1="${h - pad.b}" x2="${x}" y2="${top}" ` +
      `stroke="var(--text-dim)" stroke-width="1" opacity="0.75"><title>` +
      `${stick.position.toFixed(2)}  I=${stick.intensity.toPrecision(3)}</title></line>`;
  }).join("");

  // Four ticks per axis is enough to read a spectrum without clutter.
  const ticks = [0, 1, 2, 3, 4].map((i) => {
    const value = xMin + ((xMax - xMin) * i) / 4;
    return `<text x="${sx(value).toFixed(1)}" y="${h - pad.b + 14}" fill="var(--text-dim)" ` +
      `font-size="10" text-anchor="middle">${value >= 100 ? value.toFixed(0) : value.toFixed(2)}</text>`;
  }).join("");
  const yTicks = [0, 0.5, 1].map((f) =>
    `<text x="${pad.l - 6}" y="${(sy(f * yMax) + 3).toFixed(1)}" fill="var(--text-dim)" ` +
    `font-size="10" text-anchor="end">${(f * yMax).toPrecision(2)}</text>`).join("");

  plot.innerHTML =
    `<svg viewBox="0 0 ${w} ${h}" width="100%" role="img" aria-label="${data.x_label}">` +
    `<rect x="${pad.l}" y="${pad.t}" width="${w - pad.l - pad.r}" height="${h - pad.t - pad.b}" ` +
    `fill="none" stroke="var(--border)"/>` +
    sticks +
    `<path d="${path}" fill="none" stroke="var(--accent)" stroke-width="1.6"/>` +
    ticks + yTicks +
    `<text x="${(pad.l + w - pad.r) / 2}" y="${h - 4}" fill="var(--text-dim)" font-size="11" ` +
    `text-anchor="middle">${data.x_label}</text>` +
    `<text x="12" y="${(h - pad.b + pad.t) / 2}" fill="var(--text-dim)" font-size="11" ` +
    `text-anchor="middle" transform="rotate(-90 12 ${(h - pad.b + pad.t) / 2})">${data.y_label}</text>` +
    `</svg>`;

  const shape = specShape.value === "lorentzian" ? "Lorentzian"
    : specShape.value === "gaussian" ? "Gaussian" : "pseudo-Voigt";
  note.textContent = `${data.title ?? ""} ${shape} broadening, ` +
    `${data.sticks.length} transition${data.sticks.length === 1 ? "" : "s"}` +
    (data.estimated_intensities
      ? " — no oscillator strengths in the output, so every line is drawn at equal intensity"
      : "");
}

for (const control of [specKind, specShape, specState]) {
  control.addEventListener("change", () => { void loadSpectrum(); });
}
specWidth.addEventListener("input", syncSpectrumControls);
specWidth.addEventListener("change", () => { void loadSpectrum(); });

// ---------- image and data export ----------
document.querySelectorAll<HTMLButtonElement>(".snapshot").forEach((button) => {
  button.addEventListener("click", () => {
    const frame = document.getElementById(button.dataset.frame!) as HTMLIFrameElement | null;
    frame?.contentWindow?.postMessage({ type: "oqp-snapshot" }, window.location.origin);
  });
});

window.addEventListener("message", (event) => {
  if (event.origin !== window.location.origin) return;
  if (event.data?.type !== "oqp-snapshot-data") return;
  const image = event.data.image as string | null;
  if (!image) return;
  const link = document.createElement("a");
  link.href = image;
  link.download = "oqp-studio-view.png";
  link.click();
});

let lastSpectrum: SpectrumData | null = null;

$<HTMLButtonElement>("specCsv").addEventListener("click", () => {
  if (!lastSpectrum?.available) return;
  const header = `# ${lastSpectrum.x_label}, ${lastSpectrum.y_label}\n`;
  const curve = lastSpectrum.x
    .map((x, i) => `${x.toPrecision(8)},${lastSpectrum!.y[i].toPrecision(8)}`)
    .join("\n");
  const sticks = lastSpectrum.sticks
    .map((stick) => `# stick,${stick.position.toPrecision(8)},${stick.intensity.toPrecision(6)}`)
    .join("\n");
  download(`${specKind.value}-spectrum.csv`, `${header}${sticks}\n${curve}\n`);
});

// ---------- orbital energy level diagram ----------
// The picture GaussView and IQmol show beside the orbitals: occupied levels
// below the gap, virtuals above, the HOMA-LUMO gap read at a glance.
type LevelOrbital = { index: number; energy: number; occupancy: number | null; spin: string };

function drawLevels(orbitals: LevelOrbital[]): void {
  const card = $<HTMLDivElement>("levelCard");
  const plot = $<HTMLDivElement>("levelPlot");
  if (orbitals.length < 2) {
    card.style.display = "none";
    return;
  }
  // Only the frontier region is legible: a core level at -20 Ha would squash
  // the valence levels and the gap into a single line.
  const homoAt = orbitals.reduce(
    (best, o, i) => ((o.occupancy ?? 0) > 1e-6 ? i : best), 0);
  const homoEnergy = orbitals[homoAt].energy;
  const window = orbitals.slice(Math.max(0, homoAt - 9), homoAt + 10);
  const shown = window.filter((o) => Math.abs(o.energy - homoEnergy) <= 1.5);
  const hidden = orbitals.length - shown.length;
  const w = 300, h = 260, pad = 26;
  const energies = shown.map((o) => o.energy);
  const lo = Math.min(...energies), hi = Math.max(...energies);
  const sy = (e: number) => h - pad - ((e - lo) / (hi - lo || 1)) * (h - 2 * pad);

  const lines = shown.map((orbital) => {
    const y = sy(orbital.energy).toFixed(1);
    const occupied = (orbital.occupancy ?? 0) > 1e-6;
    const x1 = occupied ? 60 : 160, x2 = occupied ? 140 : 240;
    return `<line class="level-line" data-mo="${orbital.index}" x1="${x1}" y1="${y}" ` +
      `x2="${x2}" y2="${y}" stroke="${occupied ? "var(--accent)" : "var(--text-dim)"}" ` +
      `stroke-width="2.5"><title>MO ${orbital.index}  ${orbital.energy.toFixed(4)} Ha` +
      `${occupied ? `  occ=${orbital.occupancy}` : ""}</title></line>`;
  }).join("");

  plot.innerHTML =
    `<svg viewBox="0 0 ${w} ${h}" width="100%">` +
    `<text x="100" y="14" fill="var(--text-dim)" font-size="11" text-anchor="middle">occupied</text>` +
    `<text x="200" y="14" fill="var(--text-dim)" font-size="11" text-anchor="middle">virtual</text>` +
    lines +
    `<text x="52" y="${(sy(hi) + 4).toFixed(1)}" fill="var(--text-dim)" font-size="10" ` +
    `text-anchor="end">${hi.toFixed(2)}</text>` +
    `<text x="52" y="${(sy(lo) + 4).toFixed(1)}" fill="var(--text-dim)" font-size="10" ` +
    `text-anchor="end">${lo.toFixed(2)} Ha</text>` +
    `</svg>` +
    (hidden
      ? `<div class="hint">${hidden} level(s) outside ±1.5 Ha of the HOMO not shown</div>`
      : "");
  const lumo = orbitals[homoAt + 1];
  if (lumo) {
    const gap = (lumo.energy - homoEnergy) * 27.211386;
    plot.insertAdjacentHTML("beforeend",
      `<div class="hint">HOMO–LUMO gap ${gap.toFixed(2)} eV</div>`);
  }
  plot.querySelectorAll<SVGLineElement>(".level-line").forEach((line) => {
    line.addEventListener("click", () => {
      mapKind.value = "mo";
      orbitalSel.value = line.dataset.mo!;
      showOrbital();
    });
  });
  card.style.display = "";
}

// ---------- measurements ----------
// The viewer reports what the user clicked; both tabs show the read-out.
window.addEventListener("message", (event) => {
  if (event.origin !== window.location.origin) return;
  if (event.data?.type !== "oqp-measure") return;
  const { labels, kind, value, unit } = event.data as
    { labels: string[]; kind: string | null; value: number | null; unit: string | null };
  const text = labels.length
    ? `<span class="picked">${labels.join(" – ")}</span>` +
      (kind ? `<span class="value">${kind}: ${value!.toFixed(3)} ${unit}</span>` : "") +
      (labels.length < 2 ? '<span class="picked">pick another atom</span>' : "")
    : "";
  for (const id of ["measurePreview", "measureResult"]) {
    const box = document.getElementById(id);
    if (!box) continue;
    box.innerHTML = text;
    box.classList.toggle("on", Boolean(text));
  }
});

// ---------- menu bar ----------
// A classic pull-down bar: click a title to open it, hover to walk across the
// open menus, click anywhere else (or Esc) to close.
const menuBar = document.querySelector<HTMLElement>(".mbar")!;
const menuNote = $<HTMLDivElement>("menuNote");

function closeMenus(): void {
  menuBar.querySelectorAll(".m.open").forEach((m) => m.classList.remove("open"));
}

menuBar.querySelectorAll<HTMLElement>(".m").forEach((group) => {
  group.querySelector(".mtitle")!.addEventListener("click", (event) => {
    event.stopPropagation();
    const wasOpen = group.classList.contains("open");
    closeMenus();
    if (!wasOpen) group.classList.add("open");
  });
  group.addEventListener("mouseenter", () => {
    if (menuBar.querySelector(".m.open")) {
      closeMenus();
      group.classList.add("open");
    }
  });
});
document.addEventListener("click", closeMenus);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeMenus();
});

// The Tauri webview blocks window.open, so the backend hands the URL to the
// system browser; the direct call stays as the fallback for a plain browser.
function openExternally(url: string): void {
  fetch("/api/open-external", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  })
    .then((response) => {
      if (!response.ok) window.open(url, "_blank", "noopener");
    })
    .catch(() => { window.open(url, "_blank", "noopener"); });
}

function download(name: string, text: string): void {
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

const COMMANDS: Record<string, () => void> = {
  "open-file": () => $<HTMLInputElement>("fileInput").click(),
  pubchem: () => { showTab("builder"); $<HTMLInputElement>("pubchemName").focus(); },
  "save-xyz": () => {
    const atoms = parseAtoms(xyzArea.value);
    download("molecule.xyz", `${atoms.length}\nOQP Studio\n${atomsToText(atoms)}\n`);
  },
  "save-oqp": () => download("job.oqp", $<HTMLTextAreaElement>("input").value),
  "clear-geom": () => { xyzArea.value = ""; builderStatus.textContent = "geometry cleared"; },
  sketch: () => $<HTMLButtonElement>("sketchBtn").click(),
  preview: () => { void updatePreview(); },
  generate: () => $<HTMLButtonElement>("generate").click(),
  run: () => $<HTMLButtonElement>("runBtn").click(),
  "refresh-jobs": () => { void refreshJobs(); },
  "toggle-nav": () => setNavVisible(document.body.classList.contains("nav-hidden")),
  "reset-layout": resetLayout,
  docs: () => openExternally("https://docs.openqp.org"),
  network: () => { void openNetworkSettings(); },
  engine: () => { void installEngine(); },
  "tab-builder": () => showTab("builder"),
  "tab-method": () => showTab("method"),
  "tab-run": () => showTab("run"),
  "tab-analysis": () => showTab("analysis"),
};

menuBar.addEventListener("click", (event) => {
  const item = (event.target as HTMLElement).closest<HTMLElement>("[data-cmd]");
  if (!item) return;
  closeMenus();
  COMMANDS[item.dataset.cmd!]?.();
});

// Help entries keep the menu open so their result stays readable.
$<HTMLElement>("menuNote").addEventListener("click", (event) => event.stopPropagation());
for (const id of ["updateBtn", "releasesBtn", "aboutBtn"]) {
  $<HTMLElement>(id).addEventListener("click", (event) => event.stopPropagation());
}

$<HTMLButtonElement>("releasesBtn").addEventListener("click", () =>
  openExternally("https://github.com/Open-Quantum-Platform/oqp-studio/releases/latest"));

const COPYRIGHT = "© 2026 Open Quantum, Inc. All rights reserved.";

$<HTMLButtonElement>("aboutBtn").addEventListener("click", async () => {
  const health = await (await fetch("/api/health")).json();
  menuNote.innerHTML =
    `<div><strong>OQP Studio ${health.version}</strong></div>` +
    `<div>A graphical interface for the Open Quantum Platform.</div>` +
    `<div style="margin-top:.4rem">${COPYRIGHT}</div>`;
});

$<HTMLButtonElement>("updateBtn").addEventListener("click", async () => {
  menuNote.textContent = "checking…";
  try {
    const info = await (await fetch("/api/update-check")).json();
    if (info.available) {
      menuNote.innerHTML =
        `Version ${info.latest} is available (you have ${info.current}).<br />` +
        `<button class="ghost" id="getUpdate" style="margin-top:.4rem;padding:.3rem .8rem">` +
        `Download and install</button> ` +
        `<a href="#" id="openReleases" style="color:var(--accent)">open the release page</a>`;
      $<HTMLAnchorElement>("openReleases").addEventListener("click", (event) => {
        event.preventDefault();
        openExternally(info.url);
      });
      $<HTMLButtonElement>("getUpdate").addEventListener("click", () => {
        void installUpdate();
      });
    } else if (info.latest) {
      menuNote.textContent = `${info.current} is the latest version.`;
    } else {
      menuNote.textContent = info.detail ?? "could not check for updates";
    }
  } catch {
    menuNote.textContent = "could not check for updates";
  }
});

// ---------- network settings ----------
// A TLS-inspecting proxy is the usual reason a PubChem lookup fails, and the
// user needs a way to hand the app their network's root certificate.
const networkOverlay = $<HTMLDivElement>("networkOverlay");
const caBundle = $<HTMLInputElement>("caBundle");
const insecureSsl = $<HTMLInputElement>("insecureSsl");
const networkNote = $<HTMLSpanElement>("networkNote");

type NetworkStatus = {
  system_trust_store: boolean; ca_bundle: string; ca_bundle_found: boolean;
  insecure: boolean; settings_path: string;
};

function renderNetworkStatus(status: NetworkStatus): void {
  const lines: [string, string][] = [
    ["System trust store",
     status.system_trust_store ? "in use" : "unavailable — falling back to the bundled CA list"],
    ["Root certificate file",
     status.ca_bundle ? (status.ca_bundle_found ? status.ca_bundle : `${status.ca_bundle} (missing)`) : "none"],
    ["Certificate checks", status.insecure ? "skipped (you switched this on)" : "on"],
  ];
  $<HTMLDivElement>("networkStatus").innerHTML = rows(lines);
  caBundle.value = status.ca_bundle;
  insecureSsl.checked = status.insecure;
}

async function openNetworkSettings(): Promise<void> {
  networkNote.textContent = "";
  networkOverlay.style.display = "block";
  try {
    renderNetworkStatus(await (await fetch("/api/network")).json());
  } catch {
    networkNote.textContent = "could not read the current settings";
  }
}

$<HTMLButtonElement>("networkClose").addEventListener("click", () => {
  networkOverlay.style.display = "none";
});

// The file picker only yields a name, not a path, so the file is read and
// written next to the settings; typing a path stays available.
$<HTMLButtonElement>("caBrowse").addEventListener("click", () =>
  $<HTMLInputElement>("caFile").click());

$<HTMLInputElement>("caFile").addEventListener("change", async (event) => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  const body = new FormData();
  body.append("file", file);
  const response = await fetch("/api/network/certificate", { method: "POST", body });
  if (response.ok) {
    const status = await response.json();
    renderNetworkStatus(status);
    networkNote.textContent = "certificate stored";
  } else {
    networkNote.textContent = "could not read that certificate";
  }
});

$<HTMLButtonElement>("networkSave").addEventListener("click", async () => {
  networkNote.textContent = "saving…";
  const response = await fetch("/api/network", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ca_bundle: caBundle.value.trim(), insecure: insecureSsl.checked }),
  });
  if (response.ok) {
    renderNetworkStatus(await response.json());
    networkNote.textContent = "saved";
  } else {
    networkNote.textContent = (await response.json()).detail ?? "could not save";
  }
});

$<HTMLButtonElement>("networkTest").addEventListener("click", async () => {
  networkNote.textContent = "testing…";
  try {
    const result = await (await fetch("/api/network/test")).json();
    networkNote.textContent = result.detail;
  } catch {
    networkNote.textContent = "the test could not run";
  }
});

// One click installs: the backend downloads this platform's installer and,
// on macOS, stages a swap that runs as soon as the app quits.
async function installUpdate(): Promise<void> {
  menuNote.textContent = "starting…";
  try {
    const started = await fetch("/api/update/install", { method: "POST" });
    if (!started.ok) {
      menuNote.textContent = (await started.json()).detail ?? "could not start the update";
      return;
    }
  } catch {
    menuNote.textContent = "could not start the update";
    return;
  }

  // Poll until it finishes; the menu stays open so the progress is visible.
  for (;;) {
    await new Promise((resolve) => setTimeout(resolve, 700));
    let state: { status: string; percent: number; detail: string };
    try {
      state = await (await fetch("/api/update/status")).json();
    } catch {
      menuNote.textContent = "lost contact with the backend";
      return;
    }
    if (state.status === "downloading") {
      menuNote.textContent = `downloading… ${state.percent}%  (${state.detail})`;
    } else if (state.status === "installing") {
      menuNote.textContent = `installing… ${state.detail}`;
    } else if (state.status === "ready") {
      menuNote.innerHTML =
        "The new version is staged. Quit OQP Studio and it will replace itself " +
        "and reopen automatically.";
      return;
    } else if (state.status === "failed") {
      menuNote.textContent = `update failed: ${state.detail}`;
      return;
    }
  }
}

// The compute engine ships as its own release archive — unzip and run, no
// Python or BLAS needed — so the app can fetch the one that matches and run
// jobs without the user assembling a toolchain. The same archive works from a
// terminal for anyone who would rather not use the GUI.
async function installEngine(): Promise<void> {
  menuNote.textContent = "checking…";
  try {
    const current = await (await fetch("/api/engine")).json();
    if (current.installed) {
      menuNote.textContent = `the engine is already available: ${current.path}`;
      return;
    }
    const started = await fetch("/api/engine/install", { method: "POST" });
    if (!started.ok) {
      menuNote.textContent = (await started.json()).detail ?? "could not start the download";
      return;
    }
  } catch {
    menuNote.textContent = "could not reach the backend";
    return;
  }

  for (;;) {
    await new Promise((resolve) => setTimeout(resolve, 700));
    let state: { status: string; percent: number; detail: string };
    try {
      state = await (await fetch("/api/engine/status")).json();
    } catch {
      menuNote.textContent = "lost contact with the backend";
      return;
    }
    if (state.status === "downloading") {
      menuNote.textContent = `downloading the engine… ${state.percent}% (${state.detail})`;
    } else if (state.status === "ready") {
      menuNote.textContent = "the engine is installed — the local runner is ready";
      await loadRunners();
      return;
    } else if (state.status === "failed") {
      menuNote.textContent = `engine install failed: ${state.detail}`;
      return;
    }
  }
}

// ---------- layout: hideable sidebar and draggable splitters ----------
const NAV_DEFAULT = 210;
const SPLIT_DEFAULT = "44%";
const shield = $<HTMLDivElement>("dragShield");

function setNavVisible(visible: boolean): void {
  document.body.classList.toggle("nav-hidden", !visible);
  const tick = document.querySelector<HTMLElement>('[data-tick="nav"]');
  if (tick) tick.style.visibility = visible ? "visible" : "hidden";
  localStorage.setItem("oqp.nav.visible", String(visible));
}

function setNavWidth(px: number): void {
  const width = Math.min(360, Math.max(120, px));
  document.documentElement.style.setProperty("--nav-w", `${width}px`);
  localStorage.setItem("oqp.nav.width", String(width));
}

$<HTMLButtonElement>("navToggle").addEventListener("click", () =>
  setNavVisible(document.body.classList.contains("nav-hidden")));

// A drag needs a full-window shield: without it the pointer entering an
// iframe (the Mol* viewer) would stop delivering mousemove to this document.
function beginDrag(handle: HTMLElement, onMove: (x: number) => void): void {
  handle.classList.add("dragging");
  shield.classList.add("on");
  const move = (event: MouseEvent) => onMove(event.clientX);
  const up = () => {
    handle.classList.remove("dragging");
    shield.classList.remove("on");
    window.removeEventListener("mousemove", move);
    window.removeEventListener("mouseup", up);
  };
  window.addEventListener("mousemove", move);
  window.addEventListener("mouseup", up);
}

$<HTMLDivElement>("navGrip").addEventListener("mousedown", (event) => {
  event.preventDefault();
  beginDrag(event.currentTarget as HTMLElement, (x) => setNavWidth(x));
});

// Every two-column panel gets a splitter between its controls and its viewer.
document.querySelectorAll<HTMLElement>(".cols").forEach((cols, index) => {
  const splitter = document.createElement("div");
  splitter.className = "splitter";
  splitter.title = "Drag to resize";
  cols.insertBefore(splitter, cols.children[1]);

  const key = `oqp.split.${index}`;
  const saved = localStorage.getItem(key);
  if (saved) cols.style.setProperty("--split", saved);

  splitter.addEventListener("mousedown", (event) => {
    event.preventDefault();
    beginDrag(splitter, (x) => {
      const box = cols.getBoundingClientRect();
      const width = Math.min(box.width - 260, Math.max(260, x - box.left));
      const value = `${Math.round(width)}px`;
      cols.style.setProperty("--split", value);
      localStorage.setItem(key, value);
    });
  });

  // Double-click restores the default proportion, as most editors do.
  splitter.addEventListener("dblclick", () => {
    cols.style.setProperty("--split", SPLIT_DEFAULT);
    localStorage.removeItem(key);
  });
});

function resetLayout(): void {
  setNavVisible(true);
  setNavWidth(NAV_DEFAULT);
  document.querySelectorAll<HTMLElement>(".cols").forEach((cols, index) => {
    cols.style.setProperty("--split", SPLIT_DEFAULT);
    localStorage.removeItem(`oqp.split.${index}`);
  });
}

setNavVisible(localStorage.getItem("oqp.nav.visible") !== "false");
setNavWidth(+(localStorage.getItem("oqp.nav.width") ?? NAV_DEFAULT));

// ---------- boot ----------
xyzArea.value = atomsToText(SAMPLES.water.atoms);
buildSampleList();
buildWorkflowGrid();
selectWorkflow(WORKFLOWS[0]);
$<HTMLSpanElement>("copyright").textContent = COPYRIGHT;
fetch("/api/health")
  .then((r) => r.json())
  .then((h) => { $<HTMLSpanElement>("health").textContent = `backend: v${h.version} ✓`; })
  .catch(() => { $<HTMLSpanElement>("health").textContent = "backend: not reachable (start it on port 8814)"; });
loadRunners().catch(() => {});
updatePreview().catch(() => {});
