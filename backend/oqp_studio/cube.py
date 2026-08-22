"""Gaussian cube validation and pointwise arithmetic."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, prod

MAX_GRID_VALUES = 2_000_000


@dataclass
class Cube:
    header: list[str]
    values: list[float]
    shape: tuple[int, int, int]
    datasets: int
    geometry: tuple[tuple[float, ...], ...]
    dataset_ids: tuple[int, ...]
    axis_units: tuple[bool, bool, bool]


def _number(token: str) -> float:
    value = float(token.replace("D", "E").replace("d", "e"))
    if not isfinite(value):
        raise ValueError("cube contains a non-finite number")
    return value


def parse(text: str) -> Cube:
    lines = text.splitlines()
    if len(lines) < 7:
        raise ValueError("cube file is incomplete")
    try:
        origin_record = lines[2].split()
        if len(origin_record) not in (4, 5):
            raise ValueError
        atom_count = int(origin_record[0])
        atoms = abs(atom_count)
        axis_records = [lines[index].split() for index in (3, 4, 5)]
        if any(len(record) != 4 for record in axis_records):
            raise ValueError
        voxel_counts = tuple(int(record[0]) for record in axis_records)
        shape = tuple(abs(count) for count in voxel_counts)
        if any(size == 0 for size in shape):
            raise ValueError
    except (IndexError, ValueError) as exc:
        raise ValueError("cube header is invalid") from exc
    header_end = 6 + atoms
    if len(lines) < header_end:
        raise ValueError("cube atom header is incomplete")
    atom_records = [line.split() for line in lines[6:header_end]]
    if any(len(record) != 5 for record in atom_records):
        raise ValueError("cube atom header is invalid")
    datasets = abs(int(origin_record[4])) if len(origin_record) > 4 else 1
    if datasets < 1:
        raise ValueError("cube dataset count must be positive")
    dataset_id_values: tuple[int, ...] = ()
    if atom_count < 0:
        dataset_tokens: list[str] = []
        while header_end < len(lines):
            dataset_tokens.extend(lines[header_end].split())
            header_end += 1
            if dataset_tokens:
                try:
                    dataset_ids = int(dataset_tokens[0])
                except ValueError as exc:
                    raise ValueError("cube dataset identifiers are invalid") from exc
                if dataset_ids < 1:
                    raise ValueError("cube dataset identifiers are invalid")
                if len(dataset_tokens) >= dataset_ids + 1:
                    break
        if not dataset_tokens or len(dataset_tokens) < int(dataset_tokens[0]) + 1:
            raise ValueError("cube dataset identifier record is incomplete")
        dataset_ids = int(dataset_tokens[0])
        if len(dataset_tokens) != dataset_ids + 1:
            raise ValueError("cube dataset identifier record is invalid")
        try:
            dataset_id_values = tuple(int(token) for token in dataset_tokens[1:])
        except ValueError as exc:
            raise ValueError("cube dataset identifiers are invalid") from exc
        if datasets != 1 and datasets != dataset_ids:
            raise ValueError("cube dataset counts disagree")
        datasets = dataset_ids
    expected = prod(shape) * datasets
    if expected > MAX_GRID_VALUES:
        raise ValueError(f"cube grid is limited to {MAX_GRID_VALUES:,} values")
    try:
        values = [_number(token)
                  for line in lines[header_end:] for token in line.split()]
    except ValueError as exc:
        if "non-finite" in str(exc):
            raise
        raise ValueError("cube grid contains a nonnumeric value") from exc
    if len(values) != expected:
        raise ValueError(f"cube grid has {len(values)} values; expected {expected}")
    try:
        geometry = (
            tuple(_number(token) for token in origin_record[1:4]),
            *(tuple(_number(token) for token in record[1:4]) for record in axis_records),
            *(tuple(_number(token) for token in record) for record in atom_records),
        )
    except ValueError as exc:
        if "non-finite" in str(exc):
            raise
        raise ValueError("cube geometry header is invalid") from exc
    axis_units = tuple(count < 0 for count in voxel_counts)
    return Cube(
        lines[:header_end], values, shape, datasets, geometry, dataset_id_values, axis_units,
    )


def combine(left_text: str, right_text: str, operation: str) -> str:
    left = parse(left_text)
    right = parse(right_text)
    if left.shape != right.shape:
        raise ValueError("cube grids have different dimensions")
    if left.datasets != right.datasets:
        raise ValueError("cube grids have different dataset counts")
    if left.axis_units != right.axis_units:
        raise ValueError("cube grids use different coordinate units")
    if left.dataset_ids != right.dataset_ids:
        raise ValueError("cube grids have different dataset identifiers")
    if len(left.geometry) != len(right.geometry) or any(
        len(a) != len(b) or any(abs(x - y) > 1.0e-8 for x, y in zip(a, b))
        for a, b in zip(left.geometry, right.geometry)
    ):
        raise ValueError("cube grids use different origins, axes, or atoms")
    if operation == "difference":
        values = [a - b for a, b in zip(left.values, right.values)]
        label = "OQP Studio cube difference (left - right)"
    elif operation == "sum":
        values = [a + b for a, b in zip(left.values, right.values)]
        label = "OQP Studio cube sum (left + right)"
    else:
        raise ValueError("cube operation must be difference or sum")
    if any(not isfinite(value) for value in values):
        raise ValueError("cube arithmetic produced a non-finite value")
    output = [label, left.header[1], *left.header[2:]]
    output.extend(" ".join(f"{value:13.5E}" for value in values[index:index + 6])
                  for index in range(0, len(values), 6))
    return "\n".join(output) + "\n"
