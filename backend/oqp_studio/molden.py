"""Molden orbital parsing and cube-grid generation.

Ports the parsing and evaluation logic of OpenqpView (frontend viewer) to
Python + NumPy so molecular orbitals from OpenQP Molden files can be
rendered as cube isosurfaces by Mol*. Supports Cartesian s/p/d/f/g shells;
spherical ([5D]/[7F]/[9G]) files are reported as unsupported.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np

BOHR_TO_ANGSTROM = 0.529177210903

SYMBOLS = [
    "X", "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg",
    "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn",
    "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb",
    "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In",
    "Sn", "Sb", "Te", "I", "Xe",
]
ATOMIC_NUMBER = {symbol: z for z, symbol in enumerate(SYMBOLS)}

# Molden Cartesian component ordering per shell.
CART_POWERS: dict[str, list[tuple[int, int, int]]] = {
    "s": [(0, 0, 0)],
    "p": [(1, 0, 0), (0, 1, 0), (0, 0, 1)],
    "d": [(2, 0, 0), (0, 2, 0), (0, 0, 2), (1, 1, 0), (1, 0, 1), (0, 1, 1)],
    "f": [(3, 0, 0), (0, 3, 0), (0, 0, 3), (1, 2, 0), (2, 1, 0),
          (2, 0, 1), (1, 0, 2), (0, 1, 2), (0, 2, 1), (1, 1, 1)],
    "g": [(4, 0, 0), (0, 4, 0), (0, 0, 4), (3, 1, 0), (3, 0, 1),
          (1, 3, 0), (0, 3, 1), (1, 0, 3), (0, 1, 3), (2, 2, 0),
          (2, 0, 2), (0, 2, 2), (2, 1, 1), (1, 2, 1), (1, 1, 2)],
}


def _component_scale(powers: tuple[int, int, int]) -> float:
    """Cartesian component normalization relative to the pure (l,0,0) form."""
    total = sum(powers)
    if total < 2:
        return 1.0
    component = 1.0
    for p in powers:
        component *= math.factorial(p) / math.factorial(2 * p)
    pure = math.factorial(total) / math.factorial(2 * total)
    return math.sqrt(component / pure)


@dataclass
class BasisFunction:
    atom_index: int
    powers: tuple[int, int, int]
    exponents: np.ndarray
    coefficients: np.ndarray
    scale: float


@dataclass
class Orbital:
    index: int
    energy: float
    spin: str
    occupancy: float | None
    symmetry: str | None
    coefficients: np.ndarray


@dataclass
class MoldenData:
    atoms: list[tuple[str, float, float, float]]  # Angstrom
    basis: list[BasisFunction] = field(default_factory=list)
    orbitals: list[Orbital] = field(default_factory=list)
    supported: bool = True
    unsupported: list[str] = field(default_factory=list)


def parse_molden(text: str) -> MoldenData:
    lines = text.splitlines()

    # Atoms
    atoms: list[tuple[str, float, float, float]] = []
    start = next((i for i, ln in enumerate(lines) if re.match(r"^\[Atoms\]", ln.strip(), re.IGNORECASE)), -1)
    factor = 1.0
    if start >= 0:
        unit = re.search(r"\]\s*(\S+)", lines[start])
        if unit and unit.group(1).upper() == "AU":
            factor = BOHR_TO_ANGSTROM
        for ln in lines[start + 1 :]:
            if re.match(r"^\s*\[", ln):
                break
            parts = ln.split()
            if len(parts) < 6:
                continue
            atoms.append((parts[0], float(parts[3]) * factor,
                          float(parts[4]) * factor, float(parts[5]) * factor))
    data = MoldenData(atoms=atoms)

    # Spherical markers make the Cartesian evaluator invalid.
    spherical = set()
    for ln in lines:
        marker = ln.strip()
        if re.match(r"^\[[^\]]*5D", marker, re.IGNORECASE):
            spherical.add("d")
        if re.match(r"^\[[^\]]*7F", marker, re.IGNORECASE):
            spherical.add("f")
        if re.match(r"^\[[^\]]*9G", marker, re.IGNORECASE):
            spherical.add("g")

    # GTO basis
    start = next((i for i, ln in enumerate(lines) if re.match(r"^\[GTO\]", ln.strip(), re.IGNORECASE)), -1)
    if start >= 0:
        current_atom: int | None = None
        i = start + 1
        while i < len(lines):
            line = lines[i].strip()
            if re.match(r"^\[", line):
                break
            atom_match = re.match(r"^(\d+)(?:\s+0)?\s*$", line)
            shell_match = re.match(r"^([spdfgh])\s+(\d+)", line, re.IGNORECASE)
            if atom_match:
                current_atom = int(atom_match.group(1)) - 1
            elif shell_match and current_atom is not None:
                shell = shell_match.group(1).lower()
                nprim = int(shell_match.group(2))
                exps, coefs = [], []
                for p in range(nprim):
                    parts = lines[i + 1 + p].split()
                    exps.append(float(parts[0].replace("D", "E").replace("d", "e")))
                    coefs.append(float(parts[1].replace("D", "E").replace("d", "e")))
                if shell in spherical or shell not in CART_POWERS:
                    data.unsupported.append(shell.upper())
                else:
                    for powers in CART_POWERS[shell]:
                        data.basis.append(BasisFunction(
                            atom_index=current_atom,
                            powers=powers,
                            exponents=np.asarray(exps),
                            coefficients=np.asarray(coefs),
                            scale=_component_scale(powers),
                        ))
                i += nprim
            i += 1
    if data.unsupported:
        data.supported = False
        return data

    # MO coefficients
    start = next((i for i, ln in enumerate(lines) if re.match(r"^\[MO\]", ln.strip(), re.IGNORECASE)), -1)
    if start >= 0:
        nao = len(data.basis)
        current: Orbital | None = None
        pending_sym: str | None = None
        for ln in lines[start + 1 :]:
            line = ln.strip()
            if re.match(r"^\[", line):
                break
            if not line:
                continue
            if m := re.match(r"^Sym=\s*(\S+)", line, re.IGNORECASE):
                pending_sym = m.group(1)
                continue
            if m := re.match(r"^Ene=\s*([-+0-9.EeDd]+)", line, re.IGNORECASE):
                current = Orbital(
                    index=len(data.orbitals) + 1,
                    energy=float(m.group(1).replace("D", "E").replace("d", "e")),
                    spin="Unknown",
                    occupancy=None,
                    symmetry=pending_sym,
                    coefficients=np.zeros(nao),
                )
                data.orbitals.append(current)
                pending_sym = None
                continue
            if current is None:
                continue
            if m := re.match(r"^Spin=\s*(\S+)", line, re.IGNORECASE):
                current.spin = m.group(1)
                continue
            if m := re.match(r"^Occup=\s*([-+0-9.EeDd]+)", line, re.IGNORECASE):
                current.occupancy = float(m.group(1).replace("D", "E").replace("d", "e"))
                continue
            if m := re.match(r"^(\d+)\s+([-+0-9.EeDd]+)", line):
                ao = int(m.group(1)) - 1
                if 0 <= ao < nao:
                    current.coefficients[ao] = float(
                        m.group(2).replace("D", "E").replace("d", "e"))
    return data


def orbital_cube(data: MoldenData, mo_index: int, max_points: int = 1_100_000) -> str:
    """Gaussian cube text of one MO evaluated on a regular grid (Bohr)."""
    orbital = data.orbitals[mo_index - 1]
    coords = np.array([[a[1], a[2], a[3]] for a in data.atoms]) / BOHR_TO_ANGSTROM

    margin = 4.5  # Bohr
    lo = coords.min(axis=0) - margin
    hi = coords.max(axis=0) + margin
    span = hi - lo
    # Uniform spacing that keeps the total grid under max_points.
    spacing = max(0.25, float((span.prod() / max_points) ** (1 / 3)))
    counts = np.maximum((span / spacing).astype(int) + 1, 2)

    axes = [np.linspace(lo[d], lo[d] + spacing * (counts[d] - 1), counts[d]) for d in range(3)]
    gx, gy, gz = np.meshgrid(*axes, indexing="ij")

    values = np.zeros(gx.shape)
    for bf, coeff in zip(data.basis, orbital.coefficients):
        if abs(coeff) < 1e-10:
            continue
        ax, ay, az = coords[bf.atom_index]
        dx, dy, dz = gx - ax, gy - ay, gz - az
        r2 = dx * dx + dy * dy + dz * dz
        radial = np.zeros(gx.shape)
        for exp_a, c in zip(bf.exponents, bf.coefficients):
            radial += c * np.exp(-exp_a * r2)
        px, py, pz = bf.powers
        values += coeff * bf.scale * (dx**px) * (dy**py) * (dz**pz) * radial

    # Gaussian cube format: z runs fastest.
    out = [
        f"OQP Studio molecular orbital {orbital.index}",
        f"MO {orbital.index}  E={orbital.energy:.6f}  occ={orbital.occupancy}",
        f"{len(data.atoms):5d} {lo[0]:12.6f} {lo[1]:12.6f} {lo[2]:12.6f}",
        f"{counts[0]:5d} {spacing:12.6f} {0.0:12.6f} {0.0:12.6f}",
        f"{counts[1]:5d} {0.0:12.6f} {spacing:12.6f} {0.0:12.6f}",
        f"{counts[2]:5d} {0.0:12.6f} {0.0:12.6f} {spacing:12.6f}",
    ]
    for (symbol, *_), (x, y, z) in zip(data.atoms, coords):
        z_num = ATOMIC_NUMBER.get(symbol, 0)
        out.append(f"{z_num:5d} {float(z_num):12.6f} {x:12.6f} {y:12.6f} {z:12.6f}")
    flat = values.reshape(counts[0] * counts[1], counts[2])
    for row in flat:
        for i in range(0, len(row), 6):
            out.append(" ".join(f"{v:13.5E}" for v in row[i : i + 6]))
    return "\n".join(out) + "\n"


def atoms_to_xyz(data: MoldenData, title: str = "geometry") -> str:
    lines = [str(len(data.atoms)), title]
    for symbol, x, y, z in data.atoms:
        lines.append(f"{symbol:2s} {x:12.6f} {y:12.6f} {z:12.6f}")
    return "\n".join(lines) + "\n"


@dataclass
class NormalMode:
    index: int
    frequency: float  # cm^-1
    displacements: np.ndarray  # (natoms, 3) in Bohr


@dataclass
class VibrationData:
    atoms: list[tuple[str, float, float, float]]  # Angstrom
    modes: list[NormalMode] = field(default_factory=list)
    intensities: list[float] = field(default_factory=list)


def parse_vibrations(text: str) -> VibrationData:
    """Frequencies and normal modes from [FREQ]/[FR-COORD]/[FR-NORM-COORD]."""
    lines = text.splitlines()

    def section(header: str) -> list[str]:
        start = next(
            (i for i, ln in enumerate(lines) if ln.strip().upper() == header), -1)
        if start < 0:
            return []
        out = []
        for ln in lines[start + 1 :]:
            if re.match(r"^\s*\[", ln):
                break
            out.append(ln)
        return out

    frequencies = [float(ln) for ln in section("[FREQ]") if ln.strip()]
    intensities = [float(ln) for ln in section("[INT]") if ln.strip()]

    atoms: list[tuple[str, float, float, float]] = []
    for ln in section("[FR-COORD]"):
        parts = ln.split()
        if len(parts) >= 4:
            atoms.append((parts[0], *(float(v) * BOHR_TO_ANGSTROM for v in parts[1:4])))

    modes: list[NormalMode] = []
    current: list[list[float]] | None = None
    for ln in section("[FR-NORM-COORD]"):
        if re.match(r"^\s*vibration", ln, re.IGNORECASE):
            if current:
                modes.append(NormalMode(len(modes) + 1, 0.0, np.asarray(current)))
            current = []
            continue
        parts = ln.split()
        if current is not None and len(parts) >= 3:
            current.append([float(v) for v in parts[:3]])
    if current:
        modes.append(NormalMode(len(modes) + 1, 0.0, np.asarray(current)))
    for mode, freq in zip(modes, frequencies):
        mode.frequency = freq
    return VibrationData(atoms=atoms, modes=modes, intensities=intensities)


def mode_trajectory(vib: VibrationData, mode_index: int,
                    frames: int = 24, amplitude: float = 0.6) -> str:
    """Multi-frame XYZ oscillating along one normal mode (for animation)."""
    mode = vib.modes[mode_index - 1]
    base = np.array([[a[1], a[2], a[3]] for a in vib.atoms])
    disp = mode.displacements * BOHR_TO_ANGSTROM
    out: list[str] = []
    for k in range(frames):
        factor = amplitude * math.sin(2 * math.pi * k / frames)
        coords = base + factor * disp
        out.append(str(len(vib.atoms)))
        out.append(f"mode {mode.index}  {mode.frequency:.2f} cm-1  frame {k + 1}/{frames}")
        for (symbol, *_), (x, y, z) in zip(vib.atoms, coords):
            out.append(f"{symbol:2s} {x:12.6f} {y:12.6f} {z:12.6f}")
    return "\n".join(out) + "\n"
