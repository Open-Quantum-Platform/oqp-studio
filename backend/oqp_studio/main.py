from __future__ import annotations

import json
import os
import re
import ssl
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from . import environment
from . import network
from .jobs import JobInfo, JobRequest, manager
from .runners import available_runners


def _warm_up_rdkit() -> None:
    """Import RDKit ahead of the first request.

    The import costs a second or more in a frozen build, and it would
    otherwise be charged to whoever first converts a 2D sketch to 3D.
    """

    def load() -> None:
        try:
            from rdkit import Chem  # noqa: F401
            from rdkit.Chem import AllChem  # noqa: F401
        except ImportError:
            pass

    threading.Thread(target=load, daemon=True).start()


environment.enrich_path()
network.activate()
_warm_up_rdkit()

app = FastAPI(title="OQP Studio backend", version=__version__)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/runners")
def runners() -> dict:
    return available_runners()


@app.get("/api/runners/detail")
def runner_detail() -> dict:
    """Which runners work and, for the native one, the binary that was found."""
    return {"available": available_runners(), **environment.describe()}


@app.post("/api/jobs")
def submit_job(req: JobRequest) -> JobInfo:
    return manager.submit(req)


@app.get("/api/jobs")
def list_jobs() -> list[JobInfo]:
    return manager.list()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> JobInfo:
    info = manager.get(job_id)
    if info is None:
        raise HTTPException(status_code=404, detail="job not found")
    return info


@app.get("/api/jobs/{job_id}/log")
def job_log(job_id: str) -> dict:
    if manager.get(job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"log": manager.log_tail(job_id)}


@app.get("/api/jobs/{job_id}/files")
def job_files(job_id: str) -> list[dict]:
    if manager.get(job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")
    return manager.files(job_id)


@app.get("/api/jobs/{job_id}/files/{name}")
def job_file(job_id: str, name: str) -> FileResponse:
    path = manager.file_path(job_id, name)
    if path is None:
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path, media_type="text/plain", filename=name)


PUBCHEM_URL = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/SDF?record_type=3d"
)


def _parse_sdf_atoms(sdf: str) -> list[list]:
    """Atom list [[symbol, x, y, z], ...] from a V2000 SDF counts+atom block."""
    lines = sdf.splitlines()
    if len(lines) < 4:
        raise ValueError("SDF too short")
    natoms = int(lines[3][0:3])
    atoms = []
    for line in lines[4 : 4 + natoms]:
        x, y, z, symbol = float(line[0:10]), float(line[10:20]), float(line[20:30]), line[31:34]
        atoms.append([symbol.strip(), x, y, z])
    return atoms


@app.get("/api/pubchem/{name}")
def pubchem_lookup(name: str) -> dict:
    """Fetch a 3D structure from PubChem by compound name."""
    url = PUBCHEM_URL.format(name=urllib.parse.quote(name))
    try:
        with urllib.request.urlopen(url, timeout=15,
                                    context=network.context()) as response:
            sdf = response.read().decode()
    except urllib.error.HTTPError as exc:
        detail = f"PubChem has no 3D record for '{name}'" if exc.code == 404 else str(exc)
        raise HTTPException(status_code=404, detail=detail) from exc
    except urllib.error.URLError as exc:
        # Match on the message as well as the type: the certificate error can
        # arrive wrapped differently depending on how the request failed.
        certificate_problem = (isinstance(exc.reason, ssl.SSLCertVerificationError)
                               or "CERTIFICATE_VERIFY" in str(exc))
        if certificate_problem:
            raise HTTPException(
                status_code=502,
                detail=(
                    "PubChem's certificate could not be verified — a network that "
                    "inspects TLS traffic is the usual cause. Open File \u2192 "
                    "Network settings to point OQP Studio at your network's root "
                    "certificate. Sketching or typing coordinates needs no network."
                ),
            ) from exc
        raise HTTPException(status_code=502, detail=f"PubChem unreachable: {exc}") from exc
    except OSError as exc:
        raise HTTPException(status_code=502, detail=f"PubChem unreachable: {exc}") from exc
    try:
        atoms = _parse_sdf_atoms(sdf)
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=502, detail="could not parse PubChem SDF") from exc
    return {"name": name, "atoms": atoms}


RCSB_URL = "https://files.rcsb.org/download/{code}.pdb"


@app.get("/api/pdb/{code}")
def rcsb_lookup(code: str) -> dict:
    """Fetch an experimental structure from the RCSB Protein Data Bank.

    PubChem holds small molecules; proteins, nucleic acids and complexes come
    from the PDB, addressed by their four-character entry ID.
    """
    entry = code.strip().upper()
    if not re.fullmatch(r"[0-9A-Z]{4}", entry):
        raise HTTPException(
            status_code=400,
            detail=f"'{code}' is not a PDB ID — those are four characters, such as 1CRN",
        )
    try:
        with urllib.request.urlopen(RCSB_URL.format(code=entry), timeout=30,
                                    context=network.context()) as response:
            text = response.read().decode(errors="replace")
    except urllib.error.HTTPError as exc:
        detail = (f"the PDB has no entry {entry}" if exc.code == 404 else str(exc))
        raise HTTPException(status_code=404, detail=detail) from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY" in str(exc):
            raise HTTPException(
                status_code=502,
                detail=(
                    "The PDB's certificate could not be verified — open File \u2192 "
                    "Network settings to trust your network's root certificate."
                ),
            ) from exc
        raise HTTPException(status_code=502, detail=f"RCSB unreachable: {exc}") from exc
    return {"code": entry, "pdb": text}


_molden_cache: OrderedDict[str, object] = OrderedDict()


def _load_molden(job_id: str, name: str):
    from . import molden

    key = f"{job_id}/{name}"
    if key not in _molden_cache:
        path = manager.file_path(job_id, name)
        if path is None:
            raise HTTPException(status_code=404, detail="file not found")
        _molden_cache[key] = molden.parse_molden(path.read_text(errors="replace"))
        while len(_molden_cache) > 8:
            _molden_cache.popitem(last=False)
    return _molden_cache[key]


@app.get("/api/jobs/{job_id}/molden/{name}/orbitals")
def molden_orbitals(job_id: str, name: str) -> dict:
    data = _load_molden(job_id, name)
    if not data.supported:
        raise HTTPException(
            status_code=422,
            detail=f"spherical shells not yet supported: {', '.join(data.unsupported)}",
        )
    return {
        "atoms": len(data.atoms),
        "orbitals": [
            {
                "index": o.index,
                "energy": o.energy,
                "spin": o.spin,
                "occupancy": o.occupancy,
                "symmetry": o.symmetry,
            }
            for o in data.orbitals
        ],
    }


@app.get("/api/jobs/{job_id}/molden/{name}/geom.xyz")
def molden_geometry(job_id: str, name: str) -> PlainTextResponse:
    from . import molden

    return PlainTextResponse(molden.atoms_to_xyz(_load_molden(job_id, name), name))


@app.get("/api/jobs/{job_id}/molden/{name}/cube")
def molden_cube(job_id: str, name: str, mo: int) -> PlainTextResponse:
    from . import molden

    data = _load_molden(job_id, name)
    if not data.supported:
        raise HTTPException(status_code=422, detail="spherical shells not yet supported")
    if not 1 <= mo <= len(data.orbitals):
        raise HTTPException(status_code=404, detail="orbital index out of range")
    return PlainTextResponse(molden.orbital_cube(data, mo))


_vib_cache: OrderedDict[str, object] = OrderedDict()


def _load_vibrations(job_id: str, name: str):
    from . import molden

    key = f"{job_id}/{name}"
    if key not in _vib_cache:
        path = manager.file_path(job_id, name)
        if path is None:
            raise HTTPException(status_code=404, detail="file not found")
        _vib_cache[key] = molden.parse_vibrations(path.read_text(errors="replace"))
        while len(_vib_cache) > 8:
            _vib_cache.popitem(last=False)
    return _vib_cache[key]


@app.get("/api/jobs/{job_id}/molden/{name}/modes")
def molden_modes(job_id: str, name: str) -> dict:
    vib = _load_vibrations(job_id, name)
    return {
        "atoms": len(vib.atoms),
        "modes": [
            {
                "index": m.index,
                "frequency": m.frequency,
                "intensity": vib.intensities[i] if i < len(vib.intensities) else None,
            }
            for i, m in enumerate(vib.modes)
        ],
    }


@app.get("/api/jobs/{job_id}/molden/{name}/mode.xyz")
def molden_mode_trajectory(job_id: str, name: str, mode: int,
                           amplitude: float = 0.6) -> PlainTextResponse:
    from . import molden

    vib = _load_vibrations(job_id, name)
    if not 1 <= mode <= len(vib.modes):
        raise HTTPException(status_code=404, detail="mode index out of range")
    return PlainTextResponse(
        molden.mode_trajectory(vib, mode, amplitude=max(0.05, min(amplitude, 2.0)))
    )


_summary_cache: OrderedDict[str, dict] = OrderedDict()


def _job_summary(job_id: str) -> dict:
    from . import analysis

    if manager.get(job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")
    cached = _summary_cache.get(job_id)
    if cached is None:
        paths = [
            path for entry in manager.files(job_id)
            if (path := manager.file_path(job_id, entry["name"])) is not None
        ]
        cached = analysis.summarize(paths)
        _summary_cache[job_id] = cached
        while len(_summary_cache) > 8:
            _summary_cache.popitem(last=False)
    return cached


@app.get("/api/jobs/{job_id}/summary")
def job_summary(job_id: str, refresh: bool = False) -> dict:
    """Energies, states, frequencies, thermochemistry and properties."""
    if refresh:
        _summary_cache.pop(job_id, None)
    return _job_summary(job_id)


@app.get("/api/jobs/{job_id}/spectrum")
def job_spectrum(job_id: str, kind: str = "ir", shape: str = "lorentzian",
                 fwhm: float | None = None, state: int = 1) -> dict:
    """One broadened spectrum. Lorentzian is the default line shape."""
    from . import analysis, spectra

    if shape not in spectra.SHAPES:
        raise HTTPException(status_code=400, detail=f"unknown line shape: {shape}")
    return analysis.spectrum(_job_summary(job_id), kind, shape=shape,
                             fwhm=fwhm, state=max(1, state))


MAP_KINDS = ("density", "spin", "alpha", "beta", "esp")


@app.get("/api/jobs/{job_id}/molden/{name}/map")
def molden_map(job_id: str, name: str, kind: str = "density") -> PlainTextResponse:
    """A scalar-field cube: electron density, spin density, or the MEP."""
    from . import molden

    if kind not in MAP_KINDS:
        raise HTTPException(status_code=400, detail=f"unknown map kind: {kind}")
    data = _load_molden(job_id, name)
    if not data.supported:
        raise HTTPException(status_code=422, detail="spherical shells not yet supported")
    if kind == "esp":
        # Prefer charges the run itself exported over ones derived here.
        summary = _job_summary(job_id)
        charges = (summary["charges"].get("resp")
                   or summary["charges"].get("lowdin")
                   or summary["charges"].get("mulliken"))
        return PlainTextResponse(molden.esp_cube(data, charges))
    return PlainTextResponse(
        molden.density_cube(data, "total" if kind == "density" else kind))


@app.get("/api/jobs/{job_id}/molden/{name}/charges")
def molden_charges(job_id: str, name: str) -> dict:
    """Atomic partial charges, from the run when present, else Mulliken."""
    from . import molden

    data = _load_molden(job_id, name)
    if not data.supported:
        raise HTTPException(status_code=422, detail="spherical shells not yet supported")
    summary = _job_summary(job_id)
    for source in ("resp", "lowdin", "mulliken"):
        charges = summary["charges"].get(source)
        if charges and len(charges) == len(data.atoms):
            return {"source": source, "charges": charges}
    return {"source": "mulliken (computed here)",
            "charges": molden.mulliken_charges(data)}


# Hosts the app is allowed to hand to the system browser. The Tauri webview
# blocks window.open, so links are opened by the OS instead — and that is only
# safe for destinations the app itself chose.
EXTERNAL_HOSTS = frozenset({
    "github.com",
    "www.github.com",
    "docs.openqp.org",
    "app.openqp.org",
    "openqp.org",
    "www.rcsb.org",
    "pubchem.ncbi.nlm.nih.gov",
})


class ExternalLink(BaseModel):
    url: str


@app.post("/api/open-external")
def open_external(link: ExternalLink) -> dict:
    """Open a link in the user's normal browser."""
    import webbrowser

    parsed = urllib.parse.urlparse(link.url)
    if parsed.scheme != "https" or parsed.hostname not in EXTERNAL_HOSTS:
        raise HTTPException(status_code=400, detail=f"refusing to open {link.url}")
    # The platform opener is more dependable inside a frozen app than the
    # webbrowser module, which looks for a browser on PATH.
    import subprocess

    if sys.platform == "darwin":
        command = ["open", link.url]
    elif os.name == "nt":
        command = ["cmd", "/c", "start", "", link.url]
    else:
        command = ["xdg-open", link.url]
    try:
        subprocess.Popen(command, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"opened": link.url}
    except OSError:
        pass
    if not webbrowser.open(link.url):
        raise HTTPException(status_code=500, detail="no browser could be launched")
    return {"opened": link.url}


class NetworkSettings(BaseModel):
    ca_bundle: str = ""
    insecure: bool = False


@app.get("/api/network")
def get_network() -> dict:
    """What the app is doing about TLS, for the network settings dialog."""
    return network.status()


@app.post("/api/network")
def set_network(settings: NetworkSettings) -> dict:
    if settings.ca_bundle and not Path(settings.ca_bundle).is_file():
        raise HTTPException(status_code=400,
                            detail=f"no such file: {settings.ca_bundle}")
    network.save(settings.ca_bundle, settings.insecure)
    return network.status()


@app.post("/api/network/certificate")
async def upload_certificate(file: UploadFile = File(...)) -> dict:
    """Store a root certificate the user picked in the file dialog.

    A browser file picker hands over the contents, not a path, so the file is
    copied next to the settings and the stored path points there.
    """
    data = (await file.read()).decode("utf-8", errors="replace")
    if "BEGIN CERTIFICATE" not in data:
        raise HTTPException(
            status_code=400,
            detail="that file is not a PEM certificate (no BEGIN CERTIFICATE block)",
        )
    target = network.settings_path().with_name("network-root.pem")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(data)
    network.save(str(target), network.load()["insecure"])
    return network.status()


@app.get("/api/network/test")
def test_network() -> dict:
    """Try the PubChem host and report exactly what happened."""
    try:
        with urllib.request.urlopen(PUBCHEM_URL.format(name="water"), timeout=15,
                                    context=network.context()):
            return {"ok": True, "detail": "PubChem reachable and verified"}
    except urllib.error.HTTPError as exc:
        # The host answered, which is all this test needs to establish.
        return {"ok": True, "detail": f"PubChem reachable (HTTP {exc.code})"}
    except Exception as exc:  # noqa: BLE001 — the message is the whole point
        return {"ok": False, "detail": str(exc)}


RELEASES_API = "https://api.github.com/repos/Open-Quantum-Platform/oqp-studio/releases/latest"
RELEASES_PAGE = "https://github.com/Open-Quantum-Platform/oqp-studio/releases/latest"


def _version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3]) or (0,)


@app.get("/api/update-check")
def update_check() -> dict:
    """Compare the running version with the newest published release."""
    request = urllib.request.Request(
        RELEASES_API, headers={"Accept": "application/vnd.github+json", "User-Agent": "oqp-studio"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            release = json.load(response)
    except Exception as exc:  # noqa: BLE001 — offline, proxy or rate limit all mean "unknown"
        return {
            "current": __version__,
            "available": False,
            "detail": f"could not reach GitHub: {exc}",
            "url": RELEASES_PAGE,
        }

    latest = str(release.get("tag_name") or "").lstrip("vV")
    assets = [
        {"name": asset["name"], "url": asset["browser_download_url"]}
        for asset in release.get("assets", [])
    ]
    return {
        "current": __version__,
        "latest": latest,
        "available": bool(latest) and _version_tuple(latest) > _version_tuple(__version__),
        "url": release.get("html_url") or RELEASES_PAGE,
        "notes": (release.get("body") or "")[:400],
        "assets": assets,
    }


# Progress of a running update, polled by the UI.
_update_state: dict = {"status": "idle", "detail": "", "percent": 0}


def _run_update(assets: list[dict]) -> None:
    from . import update

    try:
        asset = update.pick_asset(assets)
        if asset is None:
            _update_state.update(status="failed",
                                 detail="no installer published for this platform")
            return
        target = Path(tempfile.gettempdir()) / asset["name"]

        def progress(done: int, total: int) -> None:
            _update_state.update(
                status="downloading",
                percent=int(done * 100 / total) if total else 0,
                detail=f"{done // 1_000_000} MB of {total // 1_000_000} MB",
            )

        _update_state.update(status="downloading", percent=0, detail=asset["name"])
        update.download(asset["url"], target, progress)

        if sys.platform == "darwin":
            _update_state.update(status="installing", percent=100, detail="unpacking…")
            detail = update.install_macos(
                target, lambda text: _update_state.update(detail=text))
            _update_state.update(status="ready", detail=detail)
        else:
            detail = update.install_elsewhere(target)
            _update_state.update(status="ready", detail=detail)
    except Exception as exc:  # noqa: BLE001 — the UI shows whatever went wrong
        _update_state.update(status="failed", detail=str(exc))


@app.post("/api/update/install")
def update_install() -> dict:
    """Download this platform's installer and stage it for installation."""
    if _update_state["status"] in ("downloading", "installing"):
        return _update_state
    info = update_check()
    if not info.get("available"):
        raise HTTPException(status_code=400, detail="already up to date")
    _update_state.update(status="downloading", percent=0, detail="starting…")
    threading.Thread(target=_run_update, args=(info.get("assets") or [],),
                     daemon=True).start()
    return _update_state


@app.get("/api/update/status")
def update_status() -> dict:
    return _update_state


_UPLOAD = File(...)


@app.post("/api/structure/open")
async def open_structure(file: UploadFile = _UPLOAD) -> dict:
    """Read a structure out of whatever file the user already has.

    Handles OpenQP's own inputs and outputs (.oqp, .inp, .log, .json,
    .molden, packed .namd.trj), the common interchange formats (.xyz, .pdb,
    .mol/.sdf, .mol2), and ChemDraw XML. Formats that carry several
    geometries come back as multiple frames.
    """
    from . import structure_io

    data = await file.read()
    name = file.filename or "structure"
    temp_path = None
    try:
        if name.lower().endswith((".trj", ".namd.trj")):
            # The packed record is read through OpenQP's memory-mapped reader,
            # which needs a real path.
            with tempfile.NamedTemporaryFile(suffix=".namd.trj", delete=False) as handle:
                handle.write(data)
                temp_path = handle.name
        structure = structure_io.parse(name, data, path=temp_path)
    except structure_io.UnsupportedFormat as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # any parse failure is about the user's file
        raise HTTPException(status_code=422, detail=f"could not read {name}: {exc}") from exc
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

    return {
        "name": name,
        "format": structure.format,
        "frames": [
            {"label": frame.label, "atoms": [[a[0], a[1], a[2], a[3]] for a in frame.atoms]}
            for frame in structure.frames
        ],
    }


class Structure3DRequest(BaseModel):
    molfile: str | None = None
    smiles: str | None = None


@app.post("/api/structure3d")
def structure_3d(req: Structure3DRequest) -> dict:
    """2D sketch (molfile) or SMILES -> 3D coordinates via RDKit ETKDG+MMFF."""
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError as exc:
        raise HTTPException(
            status_code=501,
            detail="RDKit is not installed on the backend (pip install rdkit)",
        ) from exc

    if req.molfile:
        mol = Chem.MolFromMolBlock(req.molfile)
    elif req.smiles:
        mol = Chem.MolFromSmiles(req.smiles)
    else:
        raise HTTPException(status_code=422, detail="molfile or smiles required")
    if mol is None:
        raise HTTPException(status_code=422, detail="could not parse the structure")

    mol = Chem.AddHs(mol)
    if AllChem.EmbedMolecule(mol, AllChem.ETKDGv3()) != 0:
        raise HTTPException(status_code=422, detail="3D embedding failed for this structure")
    try:
        AllChem.MMFFOptimizeMolecule(mol)
    except Exception:  # noqa: BLE001, S110 — unoptimized coordinates are still usable
        pass
    conf = mol.GetConformer()
    atoms = [
        [atom.GetSymbol(), *(round(v, 6) for v in conf.GetAtomPosition(i))]
        for i, atom in enumerate(mol.GetAtoms())
    ]
    return {"atoms": atoms}


# In-memory store of geometry previews served back to the 3D viewer.
_previews: OrderedDict[str, str] = OrderedDict()


class PreviewRequest(BaseModel):
    xyz: str


@app.post("/api/preview")
def create_preview(req: PreviewRequest) -> dict:
    preview_id = uuid.uuid4().hex[:12]
    _previews[preview_id] = req.xyz
    while len(_previews) > 50:
        _previews.popitem(last=False)
    return {"url": f"/api/preview/{preview_id}.xyz"}


@app.get("/api/preview/{name}")
def get_preview(name: str) -> PlainTextResponse:
    preview = _previews.get(name.removesuffix(".xyz"))
    if preview is None:
        raise HTTPException(status_code=404, detail="preview not found")
    return PlainTextResponse(preview)


def _frontend_dist() -> Path | None:
    """Locate the built frontend so one server (and one origin) serves both
    the UI and the API — the layout the desktop shell relies on. In dev, the
    Vite server proxies /api instead and this mount is absent."""
    env = os.environ.get("OQP_STUDIO_FRONTEND")
    candidates = [Path(env)] if env else []
    bundle_dir = getattr(sys, "_MEIPASS", None)  # PyInstaller-frozen backend
    if bundle_dir:
        candidates.append(Path(bundle_dir) / "frontend_dist")
    candidates.append(Path(__file__).resolve().parent / "web")  # installed wheel
    candidates.append(Path(__file__).resolve().parents[2] / "frontend" / "dist")
    return next((p for p in candidates if (p / "index.html").is_file()), None)


class _NoStoreStaticFiles(StaticFiles):
    """Serves the UI with caching disabled.

    The desktop shell always loads the same URL (http://127.0.0.1:<port>/)
    under the same bundle identifier, so WebKit would otherwise reuse the
    index.html it cached from a previously installed version and show a stale
    interface after an upgrade.
    """

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, must-revalidate"
        return response


_dist = _frontend_dist()
if _dist is not None:
    app.mount("/", _NoStoreStaticFiles(directory=_dist, html=True), name="frontend")
