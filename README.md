# OQP Studio

Cross-platform (Windows / macOS / Linux) desktop GUI for the
[Open Quantum Platform](https://github.com/Open-Quantum-Platform/openqp):
build molecules, prepare validated `.oqp` inputs, run OpenQP locally or
remotely, and visualize results (geometries, molecular orbitals, NTOs,
Dyson orbitals, vibrations, spectra) with publication-quality graphics.

Design document: [OQP Studio — Design Proposal](https://github.com/Open-Quantum-Platform/openqp-docs/blob/main/docs/developers/oqp-studio-proposal.md)

## Repository layout

```
frontend/   TypeScript + Vite UI; Mol*-based 3D viewer, Ketcher sketcher,
            input forms, job monitor (also deployable as a website)
backend/    Python FastAPI local server; runs jobs through pyoqp,
            execution adapters (native / WSL / SSH), Molden→cube grid engine
shell/      Tauri 2 desktop shell; produces MSI (Windows), DMG (macOS),
            AppImage/deb (Linux) installers
docs/       architecture notes and development guides
```

## Architecture (Phase 0)

```
┌────────────────────────────── OQP Studio ────────────────────────────────┐
│  Desktop shell: Tauri 2                                                  │
│  ┌──────────────────────────┐      ┌───────────────────────────────────┐ │
│  │ Frontend (TypeScript)    │ HTTP │ Local backend (Python, FastAPI)   │ │
│  │  • Builder (Ketcher 2D,  │◄────►│  • RDKit: SMILES→3D, MMFF pre-opt │ │
│  │    3D editor)            │  WS  │  • pyoqp: run jobs in-process     │ │
│  │  • Template & DB browser │      │  • Job queue                      │ │
│  │  • Input form/editor     │      │  • Grid engine: molden→MO cubes   │ │
│  │  • Mol*-based 3D viewer  │      │  • Execution adapters:            │ │
│  │  • Spectra/plots         │      │    local · WSL · SSH/SLURM        │ │
│  └──────────────────────────┘      └───────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

On Windows, OpenQP runs through the WSL adapter until the native Windows
build of the OpenQP core is available; the GUI itself is native on all
three platforms.

## Install with pip

```bash
pip install oqp-studio        # ships the server, UI, and results viewer
oqp-studio                    # opens in its own window
```

Add the extras you need: `pip install "oqp-studio[desktop,chem]"` for the
native window (pywebview) and 2D-sketch-to-3D conversion (RDKit).

## Run it as a desktop app (no browser)

After building the frontend once (see below), the backend can open its own
native window through the OS webview:

```bash
cd backend
pip install -e ".[desktop]"
oqp-studio
```

This is the interim native experience; the Tauri shell in `shell/` will
replace it with signed installers. On Linux, pywebview additionally needs
GTK (`python3-gi` + WebKit2GTK) or Qt (`pip install pywebview[qt]`).

## Development quick start

Backend (requires Python ≥ 3.10; OpenQP/pyoqp optional — mock mode without it):

```bash
cd backend
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn oqp_studio.main:app --reload --port 8814
```

Frontend (requires Node ≥ 20):

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server proxies `/api` to the backend on port 8814.

## Code signing

Installers are currently unsigned, so macOS and Windows show a first-run
warning. On macOS, clear the quarantine flag once after installing:

```bash
xattr -cr "/Applications/OQP Studio.app"
```

To skip the warning without any certificate, install the `.app.tar.gz` build
from the terminal instead — `curl` does not set the quarantine flag:

```bash
curl -L -o oqp-studio.tar.gz <tarball URL>
tar xzf oqp-studio.tar.gz -C /Applications
```

The release workflow signs and notarizes automatically once certificates are
added as repository secrets. Accredited educational institutions can obtain
the Apple Developer Program at no cost through Apple's fee waiver — see
[docs/code-signing.md](docs/code-signing.md).

## Status

Working end to end: build a molecule (2D sketcher, PubChem, samples, or raw
coordinates), pick a workflow, generate the `.oqp` input, run it through a
local OpenQP (native, WSL, or the pyoqp API), and inspect the results —
orbitals, normal modes, geometries — rendered with Mol*. Installers are built
for Windows, macOS (Apple Silicon and Intel), and Linux.

Remaining: SSH/SLURM submission, style presets and high-resolution export,
code signing (see above). See the design proposal for the full roadmap.
