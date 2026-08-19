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

## Status

Phase 0 (MVP loop) — project skeleton, backend job API with local and WSL
execution adapters, frontend placeholder. See the design proposal for the
full roadmap.
