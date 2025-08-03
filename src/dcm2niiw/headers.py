import json
from pathlib import Path
from typing import Any
from typing import Iterable

import pydicom
import typer


def read_dicom(path: Path) -> pydicom.Dataset:
    return pydicom.dcmread(path, stop_before_pixels=True)


def header_to_dict(header: pydicom.Dataset) -> dict[str, Any]:
    return header.to_json_dict()


def get_series_id(header: pydicom.Dataset) -> str:
    return header.get("SeriesInstanceUID", "")


def read_dicom_headers(paths: Iterable[Path]) -> list[pydicom.Dataset]:
    headers = []
    for path in paths:
        try:
            header = read_dicom(path)
            headers.append(header)
        except Exception as e:
            print(f"Error reading {path}: {e}")
    return headers


def get_series_id_to_filenames(paths: Iterable[Path]) -> dict[str, list[Path]]:
    series_dict = {}
    for path in paths:
        header = read_dicom(path)
        series_id = get_series_id(header)
        if series_id not in series_dict:
            series_dict[series_id] = []
        series_dict[series_id].append(path)
    return series_dict


def get_series_id_to_headers(
    paths: Iterable[Path],
    *,
    sort: bool = True,
) -> dict[str, list[pydicom.Dataset]]:
    series_dict = {}
    for path in paths:
        header = read_dicom(path)
        series_id = get_series_id(header)
        if series_id not in series_dict:
            series_dict[series_id] = []
        series_dict[series_id].append(header)

    if sort:
        for series_id, headers in series_dict.items():
            series_dict[series_id] = sort_headers_by_instance_number(headers)

    return series_dict


def sort_headers_by_instance_number(
    headers: list[pydicom.Dataset],
) -> list[pydicom.Dataset]:
    return sorted(headers, key=lambda h: h.get("InstanceNumber", 0))


def get_series_id_to_first_header(
    paths: Iterable[Path],
    *,
    as_dict: bool = False,
) -> dict[str, pydicom.Dataset | dict[str, Any]]:
    series_id_to_headers = get_series_id_to_headers(paths, sort=True)
    return {
        series_id: headers[0].to_json_dict() if as_dict else headers[0]
        for series_id, headers in series_id_to_headers.items()
        if headers
    }


def write_series_headers_json(dicom_dir: Path, output_path: Path):
    paths = dicom_dir.rglob("*.dcm")
    series_id_to_first_header_dict = get_series_id_to_first_header(paths, as_dict=True)
    with Path(output_path).open("w") as f:
        json.dump(series_id_to_first_header_dict, f, indent=2, ensure_ascii=False)


app = typer.Typer()


@app.command()
def main(
    dicom_dir: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=True,
        file_okay=False,
        help="Directory containing DICOM files",
    ),
    output_path: Path = typer.Argument(
        ...,
        dir_okay=False,
        file_okay=True,
        help="Output JSON file path for series headers",
    ),
):
    write_series_headers_json(dicom_dir, output_path)
