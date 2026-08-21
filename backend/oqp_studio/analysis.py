"""Result summaries read back from an OpenQP job directory.

Two sources are combined. The JSON export a run writes is authoritative and
carries arrays (frequencies, IR and Raman intensities, TD energies, charges);
the log fills in what JSON does not carry (SCF convergence, the energy
component table, thermochemistry) and covers runs that produced no JSON.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

EV_PER_HARTREE = 27.211386245988
NM_EV = 1239.841984
DEBYE_PER_AU = 2.541746473

_NUM = r"[-+]?\d+\.?\d*(?:[eEdD][-+]?\d+)?"


def _floats(line: str) -> list[float]:
    out = []
    for token in re.findall(_NUM, line):
        try:
            out.append(float(token.replace("d", "e").replace("D", "E")))
        except ValueError:
            pass
    return out


# --------------------------------------------------------------------------
# JSON export


def _from_json(data: dict, summary: dict) -> None:
    if isinstance(data.get("energy"), (int, float)):
        summary["energy"]["total"] = float(data["energy"])
    energies = data.get("energies")
    if isinstance(energies, list) and energies:
        summary["energy"]["states"] = [float(e) for e in energies]

    modes = data.get("frequency_modes") or {}
    freqs = modes.get("frequencies_cm-1") or data.get("frequencies_cm-1")
    if isinstance(freqs, list) and freqs:
        ir = data.get("infrared_intensities") or []
        raman = data.get("raman_activities") or []
        summary["frequencies"] = [
            {
                "index": i + 1,
                "frequency": float(f),
                "ir": float(ir[i]) if i < len(ir) else None,
                "raman": float(raman[i]) if i < len(raman) else None,
            }
            for i, f in enumerate(freqs)
        ]
        meta = data.get("vibrational_intensity_metadata") or {}
        summary["units"]["ir"] = meta.get("ir_units", "km/mol")
        summary["units"]["raman"] = meta.get("raman_units", "a.u.")

    # Excitation energies. td_energies are total energies of the response
    # roots, so the excitations are differences from the lowest root.
    td = data.get("td_energies") or data.get("OQP::td_energies")
    if isinstance(td, list) and len(td) > 1:
        _set_states(summary, [float(e) for e in td])

    dipole = data.get("dipole")
    if isinstance(dipole, list) and len(dipole) >= 3:
        _set_dipole(summary, [float(v) for v in dipole[:3]])

    symmetry = data.get("symmetry_metadata") or {}
    if symmetry.get("point_group"):
        summary["symmetry"] = {
            "point_group": symmetry.get("point_group"),
            "detected": symmetry.get("detected_point_group"),
            "enabled": bool(symmetry.get("enabled")),
        }

    for key, label in (("mulliken_charges", "mulliken"),
                       ("lowdin_charges", "lowdin"),
                       ("resp_charges", "resp")):
        charges = data.get(key)
        if isinstance(charges, list) and charges:
            summary["charges"][label] = [float(c) for c in charges]


def _set_states(summary: dict, totals: list[float]) -> None:
    ground = totals[0]
    summary["states"] = [
        {
            "index": i,
            "total": e,
            "excitation_ev": (e - ground) * EV_PER_HARTREE,
            "excitation_nm": (NM_EV / ((e - ground) * EV_PER_HARTREE)) if e > ground else None,
            "oscillator": None,
        }
        for i, e in enumerate(totals)
    ]


def _set_dipole(summary: dict, vector: list[float]) -> None:
    total = math.sqrt(sum(v * v for v in vector))
    summary["dipole"] = {
        "x": vector[0], "y": vector[1], "z": vector[2],
        "total_au": total,
        "total_debye": total * DEBYE_PER_AU,
    }


# --------------------------------------------------------------------------
# Log


ENERGY_COMPONENTS = {
    "One electron energy": "one_electron",
    "Two electron energy": "two_electron",
    "Nuclear repulsion energy": "nuclear_repulsion",
    "TOTAL energy": "total",
    "TOTAL potential energy": "potential",
    "TOTAL kinetic energy": "kinetic",
    "Virial ratio": "virial_ratio",
}

THERMO_LABELS = {
    "E(ZPE) zero-point energy": "zpe",
    "total internal energy": "internal_energy",
    "total enthalpy": "enthalpy",
    "total Gibbs free energy": "gibbs_free_energy",
    "temperature K": "temperature",
    "pressure atm": "pressure",
}


def _from_log(text: str, summary: dict) -> None:
    lines = text.splitlines()

    for line in lines:
        stripped = line.strip()
        for label, key in ENERGY_COMPONENTS.items():
            if stripped.startswith(label) and "=" in stripped:
                values = _floats(stripped.split("=", 1)[1])
                if values:
                    summary["energy"].setdefault("components", {})[key] = values[0]
        for label, key in THERMO_LABELS.items():
            if stripped.startswith(label) and ":" in stripped:
                values = _floats(stripped.split(":", 1)[1])
                if values:
                    summary["thermochemistry"][key] = values[0]

        # "Final RHF energy is  -76.32090488 after 7 iterations"
        match = re.search(r"Final\s+(\S+)\s+energy is\s+(" + _NUM + r")"
                          r"(?:\s+after\s+(\d+)\s+iterations)?", stripped)
        if match:
            summary["scf"]["method"] = match.group(1)
            summary["scf"]["energy"] = float(match.group(2))
            if match.group(3):
                summary["scf"]["iterations"] = int(match.group(3))
        if "SCF converged" in stripped:
            summary["scf"]["converged"] = True
        elif re.search(r"SCF (did not converge|not converged)", stripped, re.IGNORECASE):
            summary["scf"]["converged"] = False

        if stripped.startswith("PyOQP state"):
            values = _floats(stripped)
            if len(values) >= 2:
                summary["energy"].setdefault("final_states", {})[int(values[0])] = values[1]

    _log_frequencies(lines, summary)
    _log_states(lines, summary)
    _log_transitions(lines, summary)
    _log_ekt_roots(lines, summary)
    _log_dipole(lines, summary)


def _log_frequencies(lines: list[str], summary: dict) -> None:
    """The "Mode  Frequency(cm-1)  IR(km/mol)  Raman(activity)" table."""
    if summary["frequencies"]:
        return
    header = next((i for i, ln in enumerate(lines)
                   if "Frequency(cm-1)" in ln or "Frequency (cm-1)" in ln), -1)
    if header < 0:
        return
    has_ir = "IR" in lines[header]
    has_raman = "Raman" in lines[header]
    rows = []
    for line in lines[header + 1:]:
        values = _floats(line[match.end():])
        if len(values) < 2 or not line.strip():
            if rows:
                break
            continue
        index, frequency = int(values[0]), values[1]
        rows.append({
            "index": index,
            "frequency": frequency,
            "ir": values[2] if has_ir and len(values) > 2 else None,
            "raman": values[3] if has_raman and len(values) > 3 else None,
        })
    summary["frequencies"] = rows


# Excited-state tables differ between drivers, so match on the numbers: a row
# that starts with a state index and carries an energy in eV (and, when the
# driver prints it, an oscillator strength) is taken as a state.
_STATE_ROW = re.compile(
    r"^\s*(\d+)\s+(" + _NUM + r")\s+(" + _NUM + r")(?:\s+(" + _NUM + r"))?\s*$")


def _log_states(lines: list[str], summary: dict) -> None:
    if _log_mrsf_state_table(lines, summary):
        return
    header = next(
        (i for i, ln in enumerate(lines)
         if re.search(r"(excitation energ|excited state)", ln, re.IGNORECASE)
         and re.search(r"(eV|osc)", ln, re.IGNORECASE)),
        -1,
    )
    if header < 0:
        return
    rows = []
    for line in lines[header + 1: header + 200]:
        match = _STATE_ROW.match(line)
        if not match:
            if rows:
                break
            continue
        index = int(match.group(1))
        total = float(match.group(2))
        excitation = float(match.group(3))
        strength = float(match.group(4)) if match.group(4) else None
        rows.append({
            "index": index,
            "total": total,
            "excitation_ev": excitation,
            "excitation_nm": NM_EV / excitation if excitation > 0 else None,
            "oscillator": strength,
        })
    if not rows:
        return
    if summary["states"]:
        # Keep the JSON energies, but adopt oscillator strengths from the log.
        by_index = {row["index"]: row for row in rows}
        for state in summary["states"]:
            match = by_index.get(state["index"])
            if match and match.get("oscillator") is not None:
                state["oscillator"] = match["oscillator"]
    else:
        summary["states"] = rows


_MRSF_STATE_ROW = re.compile(r"^\s*S(\d+)\s+")


def _log_mrsf_state_table(lines: list[str], summary: dict) -> bool:
    """Read the MRSF summary table, whose first column is ``S0``, ``S1`` ….

    The table supplies the state energy, S0-relative optical transition, and
    oscillator strength even when the JSON export has no ``td_energies``.
    """
    header = next(
        (i for i, line in enumerate(lines)
         if "transition dipole moment" in line.lower()
         and "excitation(ev)" in line.lower()),
        -1,
    )
    if header < 0:
        return False
    rows = []
    for line in lines[header + 1: header + 200]:
        match = _MRSF_STATE_ROW.match(line)
        if not match:
            continue
        values = _floats(line[match.end():])
        # Energy, excitation relative to REF, excitation relative to S0,
        # <S^2>, three transition-dipole components, magnitude, oscillator.
        if len(values) < 9:
            continue
        index = int(match.group(1))
        excitation = values[2]
        rows.append({
            "index": index,
            "total": values[0],
            "excitation_ev": excitation,
            "excitation_nm": NM_EV / excitation if excitation > 0 else None,
            "oscillator": values[8],
        })
    if not rows:
        return False
    summary["states"] = rows
    return True


_TRANSITION_ROW = re.compile(r"^\s*S(\d+)\s*->\s*S(\d+)\s+")


def _log_transitions(lines: list[str], summary: dict) -> None:
    """Read state-to-state transition moments for absorption and ESA."""
    header = next(
        (i for i, line in enumerate(lines)
         if "transition" in line.lower() and "excitation" in line.lower()
         and "->" not in line),
        -1,
    )
    if header < 0:
        return
    rows = []
    for line in lines[header + 1: header + 200]:
        match = _TRANSITION_ROW.match(line)
        if not match:
            if rows and not line.strip():
                break
            continue
        values = _floats(line[match.end():])
        # Excitation eV, three dipole components, magnitude, oscillator.
        if len(values) < 6:
            continue
        rows.append({
            "from": int(match.group(1)),
            "to": int(match.group(2)),
            "excitation_ev": values[0],
            "oscillator": values[5],
        })
    if rows:
        summary["transitions"] = rows


_EKT_ROW = re.compile(
    r"^\s*(\d+)\s+(" + _NUM + r")\s+(" + _NUM + r")\s+(" + _NUM +
    r")\s+(" + _NUM + r")\s+(" + _NUM + r")\s*$")


def _log_ekt_roots(lines: list[str], summary: dict) -> None:
    """Read EKT Dyson-root tables emitted by IP and EA calculations."""
    kind: str | None = None
    for line in lines:
        lowered = line.lower()
        if "mrsf-ekt ionization potentials" in lowered:
            kind = "ip"
            continue
        if "mrsf-ekt electron affin" in lowered:
            kind = "ea"
            continue
        if kind is None:
            continue
        match = _EKT_ROW.match(line)
        if match:
            summary["ekt"][kind].append({
                "index": int(match.group(1)),
                "binding_ev": float(match.group(4)),
                "strength": float(match.group(6)),
            })
            continue
        # After the first root, a non-data line ends this table.  Resetting
        # here also makes a following EA table independently detectable.
        if summary["ekt"][kind] and line.strip() and "dyson" not in lowered:
            kind = None


def _log_dipole(lines: list[str], summary: dict) -> None:
    if summary["dipole"]:
        return
    for i, line in enumerate(lines):
        if re.search(r"dipole", line, re.IGNORECASE) and not re.search(r"transition", line, re.IGNORECASE):
            for candidate in lines[i: i + 4]:
                values = _floats(candidate)
                if len(values) >= 3:
                    _set_dipole(summary, values[:3])
                    return


# --------------------------------------------------------------------------


def summarize(paths: list[Path]) -> dict:
    """Merge every recognisable result file of one job into a summary."""
    summary: dict = {
        "energy": {}, "scf": {}, "states": [], "frequencies": [], "transitions": [],
        "ekt": {"ip": [], "ea": []},
        "thermochemistry": {}, "charges": {}, "dipole": None, "symmetry": None,
        "units": {"ir": "km/mol", "raman": "a.u."},
        "sources": [],
    }
    for path in sorted(paths):
        if path.suffix.lower() == ".json":
            try:
                data = json.loads(path.read_text(errors="replace"))
            except (ValueError, OSError):
                continue
            if isinstance(data, dict):
                _from_json(data, summary)
                summary["sources"].append(path.name)
    for path in sorted(paths):
        if path.suffix.lower() in (".log", ".out"):
            try:
                _from_log(path.read_text(errors="replace"), summary)
            except OSError:
                continue
            summary["sources"].append(path.name)

    summary["has_frequencies"] = bool(summary["frequencies"])
    summary["has_states"] = len(summary["states"]) > 1
    summary["has_oscillators"] = any(
        s.get("oscillator") is not None for s in summary["states"])
    summary["has_ekt_ip"] = bool(summary["ekt"]["ip"])
    summary["has_ekt_ea"] = bool(summary["ekt"]["ea"])
    return summary


def spectrum(summary: dict, kind: str, *, shape: str = "lorentzian",
             fwhm: float | None = None, state: int = 1, eta: float = 0.5) -> dict:
    """Build one broadened spectrum from a summary.

    kind is ir, raman, absorption, emission, esa, photoelectron or inverse_photoelectron.
    Emission follows Kasha's
    rule: the chosen state relaxes to the ground state at this geometry, which
    is why an excited-state optimisation is the calculation that makes it
    meaningful. ESA is the set of transitions upward from that same state.
    """
    from . import spectra

    if kind in ("ir", "raman"):
        rows = summary["frequencies"]
        if not rows:
            return {"available": False, "reason": "no vibrational frequencies in this job"}
        key = "ir" if kind == "ir" else "raman"
        values = [row.get(key) for row in rows]
        if all(v is None for v in values):
            return {"available": False,
                    "reason": f"no {key.upper()} intensities in this job"}
        data = spectra.vibrational_spectrum(
            [row["frequency"] for row in rows],
            [float(v or 0.0) for v in values],
            fwhm=fwhm or 20.0, shape=shape, eta=eta,
        )
        data.update({
            "available": True,
            "x_label": "Wavenumber (cm⁻¹)",
            "y_label": ("IR absorbance" if kind == "ir" else "Raman activity")
                       + f" ({summary['units'][key]} per cm⁻¹)",
            "reverse_x": True,          # IR spectra are drawn high to low
            "fwhm": fwhm or 20.0,
            "shape": shape,
        })
        return data

    if kind in ("photoelectron", "inverse_photoelectron"):
        root_kind = "ip" if kind == "photoelectron" else "ea"
        roots = summary["ekt"][root_kind]
        if not roots:
            label = "ionization-potential" if root_kind == "ip" else "electron-affinity"
            return {"available": False, "reason": f"no {label} Dyson roots in this job"}
        data = spectra.energy_spectrum(
            [root["binding_ev"] for root in roots],
            [root["strength"] for root in roots],
            fwhm_ev=fwhm or 0.3, shape=shape, eta=eta,
        )
        peak = max(data["y"], default=0.0)
        if peak > 0.0:
            data["y"] = [value / peak for value in data["y"]]
        stick_peak = max((stick["intensity"] for stick in data["sticks"]), default=0.0)
        if stick_peak > 0.0:
            for stick in data["sticks"]:
                stick["intensity"] /= stick_peak
        data.update({
            "available": True,
            "title": ("Photoelectron spectrum (IP)" if root_kind == "ip"
                      else "Inverse photoelectron spectrum (EA)"),
            "x_label": "Electron binding energy (eV)",
            "y_label": "Normalized Dyson strength",
            "reverse_x": False,
            "fwhm": fwhm or 0.3,
            "shape": shape,
            "estimated_intensities": False,
        })
        return data

    states = summary["states"]
    if len(states) < 2:
        return {"available": False, "reason": "no excited states in this job"}

    if kind == "absorption":
        transitions = [t for t in summary["transitions"] if t["from"] == 0]
        pairs = ([(t["excitation_ev"], t.get("oscillator")) for t in transitions]
                 if transitions else
                 [(s["excitation_ev"], s.get("oscillator")) for s in states[1:]])
        title = "Absorption from S0"
    elif kind == "emission":
        chosen = next((s for s in states if s["index"] == state), states[1])
        pairs = [(chosen["excitation_ev"], chosen.get("oscillator"))]
        title = f"Emission from S{chosen['index']}"
    elif kind == "esa":
        base = next((s for s in states if s["index"] == state), states[1])
        transitions = [t for t in summary["transitions"] if t["from"] == base["index"]]
        pairs = ([(t["excitation_ev"], t.get("oscillator")) for t in transitions]
                 if transitions else [
                     (s["excitation_ev"] - base["excitation_ev"], s.get("oscillator"))
                     for s in states if s["index"] > base["index"]
                 ])
        title = f"Excited-state absorption from state {base['index']}"
        if not pairs:
            return {"available": False,
                    "reason": "no states above the selected one — request more roots"}
    else:
        return {"available": False, "reason": f"unknown spectrum kind: {kind}"}

    strengths = [f for _, f in pairs]
    estimated = all(f is None for f in strengths)
    data = spectra.electronic_spectrum(
        [e for e, _ in pairs],
        [1.0 if f is None else f for f in strengths],
        fwhm_ev=fwhm or 0.3, shape=shape, eta=eta,
    )
    # The band shape is broadened on its linear energy grid, but electronic
    # spectra are conventionally read on the derived wavelength axis.
    data["x"] = data.pop("x_nm")
    for stick in data["sticks"]:
        stick["position"] = stick.pop("position_nm")
    peak = max(data["y"], default=0.0)
    if peak > 0.0:
        data["y"] = [value / peak for value in data["y"]]
        stick_peak = max((stick["intensity"] for stick in data["sticks"]), default=0.0)
        for stick in data["sticks"]:
            if stick_peak > 0.0:
                stick["intensity"] /= stick_peak
    data.update({
        "available": True,
        "title": title,
        "x_label": "Wavelength (nm)",
        "y_label": "Normalized intensity",
        "reverse_x": True,
        "fwhm": fwhm or 0.3,
        "shape": shape,
        # Say so rather than passing unit sticks off as intensities.
        "estimated_intensities": estimated,
    })
    return data
