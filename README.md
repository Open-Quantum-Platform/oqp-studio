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
backend/    Python FastAPI local server; runs jobs through local or bundled
            OpenQP commands, execution adapters (WSL / SSH), Molden→cube grid engine
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
│  │    3D editor)            │  WS  │  • OpenQP: local or bundled       │ │
│  │  • Template & DB browser │      │  • Job queue                      │ │
│  │  • Input form/editor     │      │  • Grid engine: molden→MO cubes   │ │
│  │  • Mol*-based 3D viewer  │      │  • Execution adapters:            │ │
│  │  • Spectra/plots         │      │    local · bundled · WSL · SSH    │ │
│  └──────────────────────────┘      └───────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

The compute engine is native on all three platforms, Windows included. Two
installers are published for each: the plain one downloads the engine when you
first ask for it, and the `-with-engine` one carries it, so a single download
installs an application that computes with no network afterwards. The WSL and
SSH adapters remain, for running against a cluster or an OpenQP you installed
yourself.

## Install with pip

```bash
pip install oqp-studio        # ships the server, UI, and results viewer
oqp-studio                    # opens in its own window
```

Add the extras you need: `pip install "oqp-studio[desktop,chem]"` for the
native window (pywebview) and 2D-sketch-to-3D conversion (RDKit).

## Run it as a desktop app (no browser)

After building the frontend once (see below), the backend can open its own
The published desktop application is the Tauri shell in `shell/`. It bundles
the frontend and starts the Python backend as a sidecar over standard input
and output; the installed application does not open a local HTTP port.

## Development quick start

Backend API development (requires Python ≥ 3.10; OpenQP optional — mock mode without it):

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

Then open <http://localhost:5173>. This optional browser-only loop uses the
Vite proxy; it is not used by the desktop application.

### Working on the desktop shell

The desktop shell loads the built frontend directly and sends `/api` requests
to its Python sidecar over stdio. It has one prerequisite: `externalBin` in
`tauri.conf.json` declares the frozen backend, so stage one before running it.
Build it once:

```bash
cd frontend && npm run build          # build_binary.py embeds frontend/dist
cd ../backend && pip install -e . pyinstaller && python build_binary.py
mkdir -p ../shell/src-tauri/binaries
triple=$(rustc -Vv | sed -n 's/^host: //p')
if [ "$(uname)" = "Darwin" ]; then
  cp dist/oqp-studio-backend/oqp-studio-backend \
     "../shell/src-tauri/binaries/oqp-studio-backend-$triple"
  cp -R dist/oqp-studio-backend/_internal \
     ../shell/src-tauri/binaries/oqp-studio-backend-runtime
else
  cp dist/oqp-studio-backend \
     "../shell/src-tauri/binaries/oqp-studio-backend-$triple"
fi
```

```bash
cd shell/src-tauri
cargo run
```

For a frontend edit, rerun `npm run build` before `cargo run`. For a backend
edit, rerun `python build_binary.py`, copy the sidecar again, then rerun
`cargo run`. This checks the same no-network architecture as the packaged
application without creating a release.

### Measuring startup

The frozen backend prints a timing trace to stderr, which nothing captures
when the app is launched from Finder (`backend.log` is only written when
startup *raises*). Run it directly instead — this also isolates it from Tauri:

```bash
time "/Applications/OQP Studio.app/Contents/MacOS/oqp-studio-backend" --port 8899
```

The delay before the first `startup …s` line is time spent before Python runs
at all; the gaps between lines are import and setup cost. See
[docs/handoff.md](docs/handoff.md) for what each answer implies.

## Releasing

```bash
git tag v0.1.0 && git push origin v0.1.0
```

builds every installer, attaches them and the Python wheel to a public GitHub
release, and publishes to PyPI when `PYPI_API_TOKEN` is configured. See
[docs/distribution.md](docs/distribution.md) for the channel-by-channel
picture, including why the mobile and Mac app stores do not apply.

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
local OpenQP (native or WSL), and inspect the results —
orbitals, normal modes, geometries — rendered with Mol*. Installers are built
for Windows, macOS (Apple Silicon and Intel), and Linux.

Remaining: SSH/SLURM submission, style presets and high-resolution export,
code signing (see above). See the design proposal for the full roadmap.

Picking the work up: [docs/handoff.md](docs/handoff.md) says where the project
stands, which problems are open and what has already been ruled out on each.
