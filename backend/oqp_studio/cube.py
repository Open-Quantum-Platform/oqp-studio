"""Gaussian cube validation and pointwise arithmetic."""

from __future__ import annotations

from dataclasses import dataclass
from math import prod


@dataclass
class Cube:
    header: list[str]
    values: list[float]
    shape: tuple[int, int, int]
    datasets: int


def _number(token: str) -> float:
    return float(token.replace("D", "E").replace("d", "e"))


def parse(text: str) -> Cube:
    lines = text.splitlines()
    if len(lines) < 7:
        raise ValueError("cube file is incomplete")
    try:
        origin_record = lines[2].split()
        atom_count = int(origin_record[0])
        atoms = abs(atom_count)
        shape = tuple(abs(int(lines[index].split()[0])) for index in (3, 4, 5))
    except (IndexError, ValueError) as exc:
        raise ValueError("cube header is invalid") from exc
    header_end = 6 + atoms
    if len(lines) < header_end:
        raise ValueError("cube atom header is incomplete")
    datasets = abs(int(origin_record[4])) if len(origin_record) > 4 else 1
    if datasets < 1:
        raise ValueError("cube dataset count must be positive")
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
        if datasets != 1 and datasets != dataset_ids:
            raise ValueError("cube dataset counts disagree")
        datasets = dataset_ids
    expected = prod(shape) * datasets
    try:
        values = [_number(token)
                  for line in lines[header_end:] for token in line.split()]
    except ValueError as exc:
        raise ValueError("cube grid contains a nonnumeric value") from exc
    if len(values) != expected:
        raise ValueError(f"cube grid has {len(values)} values; expected {expected}")
    return Cube(lines[:header_end], values, shape, datasets)


def _numeric_header(header: list[str]) -> list[list[float]]:
    try:
        return [[_number(token) for token in line.split()] for line in header[2:]]
    except ValueError as exc:
        raise ValueError("cube geometry header is invalid") from exc


def combine(left_text: str, right_text: str, operation: str) -> str:
    left = parse(left_text)
    right = parse(right_text)
    if left.shape != right.shape:
        raise ValueError("cube grids have different dimensions")
    if left.datasets != right.datasets:
        raise ValueError("cube grids have different dataset counts")
    left_header = _numeric_header(left.header)
    right_header = _numeric_header(right.header)
    if len(left_header) != len(right_header) or any(
        len(a) != len(b) or any(abs(x - y) > 1.0e-8 for x, y in zip(a, b))
        for a, b in zip(left_header, right_header)
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
    output = [label, left.header[1], *left.header[2:]]
    output.extend(" ".join(f"{value:13.5E}" for value in values[index:index + 6])
                  for index in range(0, len(values), 6))
    return "\n".join(output) + "\n"
