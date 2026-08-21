from pathlib import Path
from typing import ClassVar

from fastapi.testclient import TestClient

from oqp_studio.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_desktop_launcher_degrades_without_pywebview(capsys):
    from oqp_studio import desktop

    # In environments without pywebview the launcher must explain itself
    # and exit cleanly instead of crashing.
    try:
        import webview  # noqa: F401

        has_webview = True
    except ImportError:
        has_webview = False

    if not has_webview:
        assert desktop.main() == 1
        assert "pywebview" in capsys.readouterr().out


def test_runners_listed():
    res = client.get("/api/runners")
    assert res.status_code == 200
    assert set(res.json()) >= {"pyoqp", "local", "wsl"}


def test_submit_without_openqp_fails_gracefully(tmp_path, monkeypatch):
    from oqp_studio import jobs

    monkeypatch.setattr(jobs, "JOBS_ROOT", tmp_path)
    res = client.post(
        "/api/jobs",
        json={"input_text": "[input]\nsystem=O 0 0 0\n", "runner": "local"},
    )
    assert res.status_code == 200
    job_id = res.json()["id"]

    import time

    for _ in range(50):
        info = client.get(f"/api/jobs/{job_id}").json()
        if info["status"] in ("done", "failed"):
            break
        time.sleep(0.1)
    # Without an OpenQP install the job must fail with a clear error,
    # never hang or crash the server.
    assert info["status"] in ("done", "failed")

    files = client.get(f"/api/jobs/{job_id}/files").json()
    names = {f["name"] for f in files}
    assert "input.inp" in names

    res = client.get(f"/api/jobs/{job_id}/files/input.inp")
    assert res.status_code == 200
    assert "system=O 0 0 0" in res.text

    # Path escapes must 404, not leak files outside the job directory.
    res = client.get(f"/api/jobs/{job_id}/files/..%2F..%2Fpyproject.toml")
    assert res.status_code == 404


def test_oqp_style_input_saved_as_oqp(tmp_path, monkeypatch):
    from oqp_studio import jobs

    monkeypatch.setattr(jobs, "JOBS_ROOT", tmp_path)
    res = client.post(
        "/api/jobs",
        json={"input_text": 'hf/sto-3g\nenergy\ngeom="""\nO 0 0 0\n"""\n', "runner": "local"},
    )
    job_id = res.json()["id"]
    names = {f["name"] for f in client.get(f"/api/jobs/{job_id}/files").json()}
    assert "input.oqp" in names


def test_structure3d():
    res = client.post("/api/structure3d", json={"smiles": "O"})
    try:
        import rdkit  # noqa: F401
    except ImportError:
        assert res.status_code == 501
        return
    assert res.status_code == 200
    atoms = res.json()["atoms"]
    assert len(atoms) == 3  # water with added hydrogens
    assert sorted(a[0] for a in atoms) == ["H", "H", "O"]


def test_molden_parse_and_cube():
    from pathlib import Path

    from oqp_studio import molden

    sample = (
        Path(__file__).resolve().parents[2]
        / "frontend" / "public" / "viewer" / "samples" / "water-hessian-mo.molden"
    )
    data = molden.parse_molden(sample.read_text())
    assert data.supported
    assert len(data.atoms) == 3
    assert data.orbitals, "no MOs parsed"
    assert len(data.basis) == len(data.orbitals[0].coefficients)

    cube = molden.orbital_cube(data, mo_index=1, max_points=40_000)
    header = cube.splitlines()
    assert int(header[2].split()[0]) == 3  # atom count
    assert "E=" in header[1]


def test_normal_modes_and_trajectory():
    from pathlib import Path

    from oqp_studio import molden

    sample = (
        Path(__file__).resolve().parents[2]
        / "frontend" / "public" / "viewer" / "samples" / "water-hessian-mo.freq.molden"
    )
    vib = molden.parse_vibrations(sample.read_text())
    assert len(vib.atoms) == 3
    assert len(vib.modes) == 3  # water: 3N-6
    assert vib.modes[0].frequency > 0
    assert vib.modes[0].displacements.shape == (3, 3)

    traj = molden.mode_trajectory(vib, 1, frames=8)
    lines = traj.splitlines()
    assert len(lines) == 8 * (3 + 2)  # frames x (count + comment + atoms)
    assert lines[0].strip() == "3"
    assert "cm-1" in lines[1]


def test_runner_hands_the_engine_an_absolute_input_path(tmp_path):
    """The engine runs with cwd=job_dir, so a relative path would not resolve.

    It also decides where results land: an engine writes its .log and .json
    next to the input it was given.
    """
    from oqp_studio.runners.base import Runner

    class Recording(Runner):
        name = "recording"
        seen: ClassVar[list[str]] = []

        def is_available(self) -> bool:
            return True

        def build_command(self, input_file):
            Recording.seen.append(str(input_file))
            return ["true"]

    job_dir = tmp_path / "jobs_data" / "abc123"
    job_dir.mkdir(parents=True)
    (job_dir / "input.oqp").write_text("system=water\n")

    assert Recording().run(job_dir) == 0
    passed = Path(Recording.seen[-1])
    assert passed.is_absolute()
    assert passed == (job_dir / "input.oqp").resolve()


def test_imported_results_analyse_like_a_run_of_our_own(tmp_path, monkeypatch):
    """A run made elsewhere must be analysable, not just downloadable.

    Analysis is keyed on a job directory, so importing means giving foreign
    output files one; the summary and spectrum endpoints then work unchanged.
    """
    import json

    from oqp_studio import jobs

    monkeypatch.setattr(jobs, "JOBS_ROOT", tmp_path)
    export = json.dumps({
        "energy": -76.0107465151,
        "frequencies_cm-1": [1600.0, 3700.0, 3800.0],
        "infrared_intensities": [70.0, 10.0, 60.0],
    })
    res = client.post(
        "/api/jobs/import",
        files=[
            ("files", ("hf.log", "TOTAL energy =  -76.0107465151\n", "text/plain")),
            ("files", ("hf.json", export, "application/json")),
        ],
        data={"name": "cluster run"},
    )
    assert res.status_code == 200, res.text
    job_id = res.json()["id"]
    assert res.json()["runner"] == "imported"

    summary = client.get(f"/api/jobs/{job_id}/summary").json()
    assert summary["energy"]["total"] == -76.0107465151
    assert summary["has_frequencies"]
    assert client.get(f"/api/jobs/{job_id}/spectrum?kind=ir").json()["x"]


def test_importing_a_folder_takes_the_results_and_leaves_the_rest(tmp_path, monkeypatch):
    from oqp_studio import jobs

    monkeypatch.setattr(jobs, "JOBS_ROOT", tmp_path / "jobs")
    run = tmp_path / "run"
    run.mkdir()
    (run / "water.log").write_text("TOTAL energy =  -76.0\n")
    (run / "water.json").write_text("{}")
    (run / "restart.bin").write_bytes(b"\0" * 16)

    res = client.post("/api/jobs/import-path", json={"path": str(run)})
    assert res.status_code == 200, res.text
    names = [f["name"] for f in client.get(f"/api/jobs/{res.json()['id']}/files").json()]
    assert names == ["water.json", "water.log"]

    assert client.post("/api/jobs/import-path", json={"path": str(tmp_path / "no")}).status_code == 404


def test_an_import_cannot_write_outside_its_job_directory(tmp_path, monkeypatch):
    from oqp_studio import jobs

    monkeypatch.setattr(jobs, "JOBS_ROOT", tmp_path / "jobs")
    res = client.post(
        "/api/jobs/import",
        files=[("files", ("../../escaped.log", "x", "text/plain"))],
    )
    assert res.status_code == 200, res.text
    assert not (tmp_path / "escaped.log").exists()
    names = [f["name"] for f in client.get(f"/api/jobs/{res.json()['id']}/files").json()]
    assert names == ["escaped.log"]


def test_an_installer_that_carries_the_engine_needs_no_download(tmp_path, monkeypatch):
    """An all-in-one installer must just work: no download, no configuration.

    The shell tells the backend where its resources went, because that
    directory is in a different place on every platform.
    """
    import os
    import stat

    from oqp_studio import engine, environment

    resources = tmp_path / "resources"
    (resources / "engine").mkdir(parents=True)
    executable = resources / "engine" / engine.EXECUTABLE
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(executable.stat().st_mode | stat.S_IEXEC)

    monkeypatch.setenv("OQP_STUDIO_RESOURCES", str(resources))
    monkeypatch.setattr(engine, "data_dir", lambda: tmp_path / "unused")
    # No engine of the user's own on PATH, so the bundled one is what is found.
    monkeypatch.setattr(environment, "locate", lambda command: None)

    assert engine.bundled_dir() == resources / "engine"
    assert engine.locate() == str(executable)
    assert engine.status()["source"] == "included with the installer"
    assert os.access(executable, os.X_OK)


def test_updating_an_all_in_one_install_keeps_the_engine(monkeypatch):
    """The slim installer would replace the directory the engine lives in.

    Someone who installed the all-in-one must be offered the all-in-one
    again, or the update would silently leave them unable to compute.
    """
    from oqp_studio import engine, update

    monkeypatch.setattr(update, "_platform_asset", lambda: ("windows-x64", "-setup.exe"))
    assets = [
        {"name": "OQP-Studio-0.2.0-windows-x64-setup.exe"},
        {"name": "OQP-Studio-0.2.0-windows-x64-with-engine-setup.exe"},
    ]

    monkeypatch.setattr(engine, "bundled_dir", lambda: None)
    assert update.pick_asset(assets)["name"].endswith("windows-x64-setup.exe")

    monkeypatch.setattr(engine, "bundled_dir", lambda: object())
    assert update.pick_asset(assets)["name"].endswith("with-engine-setup.exe")

    # A release that published no all-in-one still updates the app.
    assert update.pick_asset(assets[:1])["name"].endswith("windows-x64-setup.exe")
