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
